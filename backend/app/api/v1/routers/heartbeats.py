"""Heartbeat CRUD + public ping (Phase 5).

POST   /heartbeats            Member+  create, returns ping_key ONCE
GET    /heartbeats            Bearer   list with ALIVE/MISSING
DELETE /heartbeats/{id}       Member+  delete (rotates the secret by recreate)
POST   /heartbeats/{key}/ping public   cron proof-of-life, key auth, no JWT
"""

import secrets
import uuid

from fastapi import APIRouter, Request, status

from app.api.deps import DBDep, MemberUser, client_ip
from app.core.exceptions import AppError
from app.core.redis import redis_client
from app.repositories import audit_repository, heartbeat_repository
from app.schemas.common import ApiResponse
from app.schemas.heartbeat import HeartbeatCreatedOut, HeartbeatIn, HeartbeatOut
from app.services import telegram_service
from app.services.live_service import invalidate_public_cache

router = APIRouter(prefix="/heartbeats", tags=["heartbeats"])


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[HeartbeatCreatedOut]
)
async def create_heartbeat(user: MemberUser, body: HeartbeatIn, request: Request, db: DBDep):
    ping_key = f"hb_{secrets.token_urlsafe(24)}"
    hb = await heartbeat_repository.create(
        db,
        team_id=user.team_id,
        name=body.name.strip(),
        ping_key=ping_key,
        period_min=body.period_min,
        grace_min=body.grace_min,
        status="ALIVE",
    )
    await audit_repository.log(
        db,
        action="heartbeat.created",
        team_id=user.team_id,
        user_id=user.id,
        target_type="heartbeat",
        target_id=str(hb.id),
        detail={"name": hb.name, "period_min": hb.period_min, "grace_min": hb.grace_min},
        ip=client_ip(request),
    )
    await db.commit()
    data = {**hb.__dict__, "ping_key": ping_key}
    return ApiResponse(data=HeartbeatCreatedOut.model_validate(data))


@router.get("", response_model=ApiResponse[list[HeartbeatOut]])
async def list_heartbeats(user: MemberUser, db: DBDep):
    rows = await heartbeat_repository.list_for_team(db, user.team_id)
    return ApiResponse(data=[HeartbeatOut.model_validate(r) for r in rows])


@router.delete("/{heartbeat_id}", response_model=ApiResponse[dict])
async def delete_heartbeat(user: MemberUser, heartbeat_id: uuid.UUID, request: Request, db: DBDep):
    hb = await heartbeat_repository.get_by_id(db, heartbeat_id)
    if hb is None or hb.team_id != user.team_id:
        raise AppError(404, "NOT_FOUND", "Heartbeat not found")
    await audit_repository.log(
        db,
        action="heartbeat.deleted",
        team_id=user.team_id,
        user_id=user.id,
        target_type="heartbeat",
        target_id=str(hb.id),
        ip=client_ip(request),
    )
    await heartbeat_repository.delete(db, hb)
    await db.commit()
    return ApiResponse(data={"deleted": True})


@router.post("/{ping_key}/ping", response_model=ApiResponse[dict])
async def ping_heartbeat(ping_key: str, db: DBDep):
    """Public proof-of-life. Key auth only — no JWT, rate-limited by key in prod."""
    from datetime import UTC, datetime

    hb = await heartbeat_repository.get_by_key(db, ping_key)
    if hb is None:
        raise AppError(404, "NOT_FOUND", "Unknown ping key")
    was_missing = hb.status == "MISSING"
    hb.last_ping_at = datetime.now(UTC)
    hb.status = "ALIVE"
    await db.commit()

    if was_missing:
        # Recovery alert on the same Telegram channels as monitors.
        from app.repositories import alert_log_repository, notification_channel_repository

        channels = await notification_channel_repository.list_active_for_team(db, hb.team_id)
        text = telegram_service.build_heartbeat_recovery_message(hb.name)
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
                kind="recovery",
                status="sent" if ok else "failed",
                error=error,
                telegram_message_id=msg_id,
            )
        await db.commit()
        try:
            from app.models.team import Team

            team = await db.get(Team, hb.team_id)
            await invalidate_public_cache(redis_client, team.slug if team else None)
        except Exception:  # noqa: BLE001
            pass
    return ApiResponse(data={"ok": True, "status": hb.status})
