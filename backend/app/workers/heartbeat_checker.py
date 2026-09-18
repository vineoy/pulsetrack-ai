"""Heartbeat checker cron (Phase 5): silence past period+grace = MISSING + Telegram.

Runs every minute. For each ALIVE heartbeat with last_ping_at older than
now - (period_min + grace_min) — or never pinged and older than window since
creation — mark MISSING and alert on the team's existing Telegram channels.
Alert log uses kind="open" with monitor/incident None (fits the CHECK
constraint; v1 has no incident row for heartbeats by design).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.db import async_session_factory
from app.models.heartbeat import Heartbeat
from app.repositories import alert_log_repository, notification_channel_repository
from app.services import telegram_service


async def heartbeat_checker(ctx: dict | None = None) -> str:
    now = datetime.now(UTC)
    checked = 0
    missing = 0
    async with async_session_factory() as db:
        result = await db.execute(select(Heartbeat).where(Heartbeat.status == "ALIVE"))
        heartbeats = list(result.scalars().all())
        for hb in heartbeats:
            window = timedelta(minutes=hb.period_min + hb.grace_min)
            baseline = hb.last_ping_at or hb.created_at
            if baseline is None or now - baseline < window:
                continue
            checked += 1
            hb.status = "MISSING"
            silent_min = max(1, int((now - baseline).total_seconds() // 60))
            channels = await notification_channel_repository.list_active_for_team(db, hb.team_id)
            text = telegram_service.build_heartbeat_down_message(hb.name, silent_min)
            if not channels:
                await alert_log_repository.create(
                    db,
                    team_id=hb.team_id,
                    incident_id=None,
                    channel_id=None,
                    monitor_id=None,
                    kind="open",
                    status="skipped",
                    error="no active telegram channel",
                )
            for channel in channels:
                ok, error, msg_id = await telegram_service.send_message(
                    channel.telegram_chat_id, text
                )
                await alert_log_repository.create(
                    db,
                    team_id=hb.team_id,
                    incident_id=None,
                    channel_id=channel.id,
                    monitor_id=None,
                    kind="open",
                    status="sent" if ok else "failed",
                    attempts=telegram_service.MAX_RETRIES if not ok else 1,
                    error=error,
                    telegram_message_id=msg_id,
                )
            missing += 1
        await db.commit()
    return f"ok checked={checked} missing={missing}"
