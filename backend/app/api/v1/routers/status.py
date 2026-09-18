"""Public status page API (Phase 5) — no auth, Redis-cached, privacy-safe.

GET /status/{slug}            team + monitors + overall (cached 30s)
GET /status/{slug}/incidents  recent incidents with monitor names (cached 30s)

Privacy: monitor names + statuses only — never URLs, emails, chat IDs.
Cache: public:{slug}, public:{slug}:incidents.
Invalidation: worker deletes these keys when a check flips status or an
incident opens/resolves (see live_service.invalidate_public_cache).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DBDep, RedisDep
from app.core.exceptions import AppError
from app.models.incident import IncidentStatus
from app.models.monitor import Monitor
from app.repositories import check_repository, incident_repository, team_repository
from app.schemas.status import PublicIncidentOut, PublicStatusOut
from app.services.live_service import public_incidents_key, public_status_key

router = APIRouter(prefix="/status", tags=["status"])

STATUS_TTL = 30


def _overall(monitors: list[dict], open_count: int) -> str:
    if open_count > 0 or any(m["current_status"] == "DOWN" for m in monitors):
        downs = sum(1 for m in monitors if m["current_status"] == "DOWN")
        total = len([m for m in monitors if m["current_status"] != "PAUSED"])
        if total and downs >= total:
            return "outage"
        return "degraded"
    return "operational"


@router.get("/{slug}", response_model=dict)
async def public_status(slug: str, db: DBDep, redis: RedisDep):
    key = public_status_key(slug)
    try:
        cached = await redis.get(key)
    except Exception:  # noqa: BLE001
        cached = None
    if cached:
        try:
            return {"data": json.loads(cached), "error": None}
        except (json.JSONDecodeError, TypeError):
            pass

    team = await team_repository.get_by_slug(db, slug)
    if team is None:
        raise AppError(404, "NOT_FOUND", "Status page not found")

    result = await db.execute(select(Monitor).where(Monitor.team_id == team.id))
    monitors = list(result.scalars().all())
    latest = await check_repository.latest_per_monitor(db, [m.id for m in monitors])
    rows: list[dict] = []
    for monitor in monitors:
        last = latest.get(monitor.id)
        if monitor.is_paused:
            current = "PAUSED"
        elif last is None:
            current = "PENDING"
        else:
            current = last.status
        rows.append(
            {
                "id": str(monitor.id),
                "name": monitor.name,
                "current_status": current,
                "last_latency_ms": last.latency_ms if last else None,
                "last_checked_at": last.checked_at.isoformat() if last else None,
            }
        )

    open_incidents = await incident_repository.list_for_team(
        db, team.id, status=IncidentStatus.OPEN
    )
    payload = {
        "team_name": team.name,
        "slug": team.slug,
        "overall": _overall(rows, len(open_incidents)),
        "open_incidents": len(open_incidents),
        "monitors": rows,
    }
    # Validate shape before caching so a bug can't poison the cache.
    PublicStatusOut(
        **{
            **payload,
            "monitors": [
                {
                    **m,
                    "last_checked_at": m["last_checked_at"],
                }
                for m in rows
            ],
        }
    )
    try:
        await redis.set(key, json.dumps(payload), ex=STATUS_TTL)
    except Exception:  # noqa: BLE001
        pass
    return {"data": payload, "error": None}


@router.get("/{slug}/incidents", response_model=dict)
async def public_incidents(
    slug: str,
    db: DBDep,
    redis: RedisDep,
    limit: int = Query(default=20, ge=1, le=100),
):
    key = public_incidents_key(slug)
    try:
        cached = await redis.get(key)
    except Exception:  # noqa: BLE001
        cached = None
    if cached:
        try:
            items = json.loads(cached)
            return {"data": items[:limit], "error": None}
        except (json.JSONDecodeError, TypeError):
            pass

    team = await team_repository.get_by_slug(db, slug)
    if team is None:
        raise AppError(404, "NOT_FOUND", "Status page not found")

    incidents = await incident_repository.list_for_team(db, team.id)
    result = await db.execute(select(Monitor).where(Monitor.team_id == team.id))
    names = {m.id: m.name for m in result.scalars().all()}
    items = [
        {
            "id": str(inc.id),
            "monitor_name": names.get(inc.monitor_id, "Monitor"),
            "status": inc.status,
            "started_at": inc.started_at.isoformat(),
            "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
            "downtime_sec": inc.downtime_sec,
        }
        for inc in incidents
    ]
    for item in items:
        PublicIncidentOut(**item)
    try:
        await redis.set(key, json.dumps(items), ex=STATUS_TTL)
    except Exception:  # noqa: BLE001
        pass
    return {"data": items[:limit], "error": None}
