"""Telegram auto-connect poller (Option A - polling, 100% free).

Runs as an ARQ cron every 30s. Calls getUpdates, looks for '/start <token>'
messages, matches the one-time token created by POST /connect, and
auto-creates the notification_channel. Sends a 'connected' confirmation.

Never raises: returns a short summary string so ARQ logs stay readable.
"""

from __future__ import annotations

import uuid

from app.core.db import async_session_factory
from app.core.redis import redis_client
from app.repositories import audit_repository, notification_channel_repository
from app.services import telegram_link_service, telegram_service


async def poll_telegram_updates(ctx: dict | None = None) -> str:
    token = telegram_service.get_bot_token()
    if not token:
        return "skipped:no_token"

    offset = await telegram_link_service.get_offset(redis_client)
    updates, error = await telegram_service.get_updates(offset)
    if error:
        return f"skipped:{error[:80]}"

    connected = 0
    seen = 0
    for update in updates:
        try:
            update_id = update.get("update_id")
        except AttributeError:
            continue
        if isinstance(update_id, int):
            seen = max(seen, update_id + 1)
        message = (update or {}).get("message") or (update or {}).get("edited_message")
        if not isinstance(message, dict):
            continue
        text = message.get("text")
        invite_token = telegram_service.parse_start_payload(text)
        if not invite_token:
            continue
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            continue
        chat_id_str = str(chat_id)
        # Basic sanity: Telegram chat ids are integers
        if not chat_id_str.lstrip("-").isdigit():
            continue

        payload = await telegram_link_service.consume_link(redis_client, invite_token)
        if payload is None:
            continue
        try:
            team_id = uuid.UUID(str(payload.get("team_id")))
            user_id = uuid.UUID(str(payload.get("user_id")))
        except (ValueError, TypeError):
            continue
        label = payload.get("label")

        async with async_session_factory() as db:
            existing = await notification_channel_repository.find_by_chat_id(
                db, team_id, chat_id_str
            )
            if existing is not None:
                channel = existing
            else:
                channel = await notification_channel_repository.create(
                    db, team_id=team_id, telegram_chat_id=chat_id_str, label=label
                )
                await audit_repository.log(
                    db,
                    action="notification_channel.created",
                    team_id=team_id,
                    user_id=user_id,
                    target_type="notification_channel",
                    target_id=str(channel.id),
                    detail={
                        "telegram_chat_id": chat_id_str,
                        "label": label,
                        "via": "telegram_auto_connect",
                    },
                )
                await db.commit()
            # Best-effort welcome message (never fails the connect)
            try:
                team_name = None
                try:
                    from app.models.team import Team

                    team = await db.get(Team, team_id)
                    team_name = team.name if team else None
                except Exception:  # noqa: BLE001
                    team_name = None
                await telegram_service.send_message(
                    chat_id_str, telegram_service.build_connected_message(team_name)
                )
            except Exception:  # noqa: BLE001
                pass
            await telegram_link_service.mark_connected(
                redis_client, invite_token, channel.id
            )
            connected += 1

    if seen:
        # Advance offset even when no /start found, so we never re-read.
        next_offset = seen
        if offset is not None:
            next_offset = max(seen, offset)
        await telegram_link_service.set_offset(redis_client, next_offset)

    return f"ok connected={connected} scanned={len(updates)}"
