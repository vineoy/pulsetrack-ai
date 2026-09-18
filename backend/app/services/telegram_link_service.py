"""One-time Telegram connect tokens (Option A - polling).

Flow: POST /notification-channels/connect creates token -> stored in Redis
`tg_link:{token}` with 15 min TTL -> deep link t.me/Bot?start={token} ->
user presses Start -> worker poller matches token -> auto-creates channel.

All helpers accept an explicit redis client so tests can inject fakeredis /
test DB. Production code passes the global redis_client.
"""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import UTC, datetime

from app.core.config import get_settings

LINK_PREFIX = "tg_link:"
DONE_PREFIX = "tg_link_done:"
OFFSET_KEY = "tg_update_offset"


def _link_key(token: str) -> str:
    return f"{LINK_PREFIX}{token}"


def _done_key(token: str) -> str:
    return f"{DONE_PREFIX}{token}"


async def create_link(
    redis,
    *,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    label: str | None = None,
) -> dict:
    """Create a single-use connect token. Returns {token, expires_in_sec}."""
    token = secrets.token_urlsafe(24)
    expire_min = get_settings().telegram_link_expire_min
    payload = {
        "team_id": str(team_id),
        "user_id": str(user_id),
        "label": label,
        "created_at": datetime.now(UTC).isoformat(),
    }
    await redis.set(_link_key(token), json.dumps(payload), ex=expire_min * 60)
    return {"token": token, "expires_in_sec": expire_min * 60}


async def get_link(redis, token: str) -> dict | None:
    raw = await redis.get(_link_key(token))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


async def consume_link(redis, token: str) -> dict | None:
    """Fetch + delete the pending link. Returns payload or None."""
    data = await get_link(redis, token)
    if data is None:
        return None
    await redis.delete(_link_key(token))
    return data


async def mark_connected(redis, token: str, channel_id: uuid.UUID) -> None:
    """Remember token -> channel so the UI status poll can resolve instantly."""
    await redis.set(_done_key(token), str(channel_id), ex=10 * 60)


async def get_connected_channel_id(redis, token: str) -> str | None:
    raw = await redis.get(_done_key(token))
    return str(raw) if raw else None


async def cancel_link(redis, token: str) -> bool:
    return bool(await redis.delete(_link_key(token)))


async def get_offset(redis) -> int | None:
    raw = await redis.get(OFFSET_KEY)
    if raw is None:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


async def set_offset(redis, offset: int) -> None:
    await redis.set(OFFSET_KEY, str(offset))
