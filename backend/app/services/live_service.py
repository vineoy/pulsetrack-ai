"""Live fan-out: worker publishes each finished check, WS forwards team-only events.

Channel: "live" (Redis pub/sub, fire-and-forget).
Message: {team_id, monitor_id, status, latency_ms, status_code, checked_at,
          incident: "OPEN" | "RESOLVED" | None}
Public-status cache invalidation also lives here so checker.py stays thin.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

LIVE_CHANNEL = "live"


def build_check_event(
    *,
    team_id: uuid.UUID | str,
    monitor_id: uuid.UUID | str,
    status: str,
    latency_ms: int | None,
    status_code: int | None,
    checked_at: datetime,
    incident: str | None = None,
) -> dict:
    return {
        "type": "check",
        "team_id": str(team_id),
        "monitor_id": str(monitor_id),
        "status": status,
        "latency_ms": latency_ms,
        "status_code": status_code,
        "checked_at": checked_at.isoformat(),
        "incident": incident,
    }


async def publish_check(redis, event: dict) -> None:
    """Best-effort publish. Never raises — live must never fail a check."""
    try:
        await redis.publish(LIVE_CHANNEL, json.dumps(event))
    except Exception:  # noqa: BLE001
        pass


def public_status_key(slug: str) -> str:
    return f"public:{slug}"


def public_incidents_key(slug: str) -> str:
    return f"public:{slug}:incidents"


async def invalidate_public_cache(redis, slug: str | None) -> None:
    """Delete cached public status pages for a team slug. Best-effort."""
    if not slug:
        return
    try:
        await redis.delete(public_status_key(slug), public_incidents_key(slug))
    except Exception:  # noqa: BLE001
        pass
