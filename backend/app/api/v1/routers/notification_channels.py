import uuid

from fastapi import APIRouter, Request, status

from app.api.deps import DBDep, MemberUser, RedisDep, client_ip
from app.repositories import audit_repository, notification_channel_repository
from app.schemas.common import ApiResponse
from app.schemas.notification_channel import (
    TelegramChannelIn,
    TelegramChannelOut,
    TelegramConnectIn,
    TelegramConnectOut,
    TelegramConnectStatusOut,
    TelegramTestOut,
)
from app.services import telegram_link_service, telegram_service

router = APIRouter(prefix="/notification-channels", tags=["notifications"])


@router.get("", response_model=ApiResponse[list[TelegramChannelOut]])
async def list_channels(user: MemberUser, db: DBDep):
    rows = await notification_channel_repository.list_for_team(db, user.team_id)
    return ApiResponse(data=[TelegramChannelOut.model_validate(r) for r in rows])


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[TelegramChannelOut]
)
async def create_channel(
    user: MemberUser, body: TelegramChannelIn, request: Request, db: DBDep
):
    # Normalize chat_id: strip spaces; keep minus for supergroups
    chat_id = body.telegram_chat_id.strip()
    # Basic sanity: must look like an integer id (Telegram chat ids are integers)
    stripped = chat_id.lstrip("-")
    if not stripped.isdigit():
        from app.core.exceptions import AppError

        raise AppError(
            422,
            "VALIDATION_ERROR",
            "telegram_chat_id must be numeric, e.g. 123456789 or -1001234567890",
        )
    channel = await notification_channel_repository.create(
        db, team_id=user.team_id, telegram_chat_id=chat_id, label=body.label
    )
    await audit_repository.log(
        db,
        action="notification_channel.created",
        team_id=user.team_id,
        user_id=user.id,
        target_type="notification_channel",
        target_id=str(channel.id),
        detail={"telegram_chat_id": chat_id, "label": body.label},
        ip=client_ip(request),
    )
    await db.commit()
    return ApiResponse(data=TelegramChannelOut.model_validate(channel))


@router.post(
    "/connect", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[TelegramConnectOut]
)
async def create_connect_link(
    user: MemberUser, body: TelegramConnectIn, redis: RedisDep
):
    """Start auto-connect: returns one-time t.me deep link (15 min expiry).

    No chat_id typing needed. User opens the link, presses Start in Telegram,
    worker poller picks up /start <token> via getUpdates and auto-creates
    the channel. Frontend polls GET /connect/{token}/status.
    """
    link = await telegram_link_service.create_link(
        redis, team_id=user.team_id, user_id=user.id, label=body.label
    )
    return ApiResponse(
        data=TelegramConnectOut(
            token=link["token"],
            deep_link=telegram_service.build_deep_link(link["token"]),
            expires_in_sec=link["expires_in_sec"],
        )
    )


@router.get(
    "/connect/{token}/status", response_model=ApiResponse[TelegramConnectStatusOut]
)
async def connect_status(user: MemberUser, token: str, redis: RedisDep, db: DBDep):
    """Pollable status for the Connect flow: pending | connected | expired."""
    channel_id = await telegram_link_service.get_connected_channel_id(redis, token)
    if channel_id:
        try:
            cid = uuid.UUID(str(channel_id))
        except ValueError:
            cid = None
        if cid is not None:
            channel = await notification_channel_repository.get_by_id(db, cid)
            if channel is not None and channel.team_id == user.team_id:
                return ApiResponse(
                    data=TelegramConnectStatusOut(
                        status="connected",
                        channel=TelegramChannelOut.model_validate(channel),
                    )
                )
    pending = await telegram_link_service.get_link(redis, token)
    if pending is not None:
        # Tenancy: token belongs to this team only
        if str(pending.get("team_id")) != str(user.team_id):
            from app.core.exceptions import AppError

            raise AppError(404, "NOT_FOUND", "Connect link not found")
        return ApiResponse(data=TelegramConnectStatusOut(status="pending", channel=None))
    return ApiResponse(data=TelegramConnectStatusOut(status="expired", channel=None))


@router.delete("/connect/{token}", response_model=ApiResponse[dict])
async def cancel_connect_link(user: MemberUser, token: str, redis: RedisDep):
    pending = await telegram_link_service.get_link(redis, token)
    if pending is not None and str(pending.get("team_id")) != str(user.team_id):
        from app.core.exceptions import AppError

        raise AppError(404, "NOT_FOUND", "Connect link not found")
    await telegram_link_service.cancel_link(redis, token)
    return ApiResponse(data={"cancelled": True})


@router.delete("/{channel_id}", response_model=ApiResponse[dict])
async def delete_channel(
    user: MemberUser, channel_id: uuid.UUID, request: Request, db: DBDep
):
    channel = await notification_channel_repository.get_by_id(db, channel_id)
    if channel is None or channel.team_id != user.team_id:
        from fastapi import status as http_status

        from app.core.exceptions import AppError

        raise AppError(http_status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Channel not found")
    await audit_repository.log(
        db,
        action="notification_channel.deleted",
        team_id=user.team_id,
        user_id=user.id,
        target_type="notification_channel",
        target_id=str(channel.id),
        ip=client_ip(request),
    )
    await notification_channel_repository.delete(db, channel)
    await db.commit()
    return ApiResponse(data={"deleted": True})


@router.post("/{channel_id}/test", response_model=ApiResponse[TelegramTestOut])
async def test_channel(user: MemberUser, channel_id: uuid.UUID, db: DBDep):
    channel = await notification_channel_repository.get_by_id(db, channel_id)
    if channel is None or channel.team_id != user.team_id:
        from fastapi import status as http_status

        from app.core.exceptions import AppError

        raise AppError(http_status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Channel not found")

    # Pick any monitor for a richer test line, fallback to generic
    from sqlalchemy import select

    from app.models.monitor import Monitor
    from app.repositories import alert_log_repository

    result = await db.execute(
        select(Monitor).where(Monitor.team_id == user.team_id).limit(1)
    )
    monitor = result.scalar_one_or_none()
    text = telegram_service.build_test_message(monitor.name if monitor else None)
    ok, error, msg_id = await telegram_service.send_message(channel.telegram_chat_id, text)
    await alert_log_repository.create(
        db,
        team_id=channel.team_id,
        incident_id=None,
        channel_id=channel.id,
        monitor_id=monitor.id if monitor else None,
        kind="test",
        status="sent" if ok else "failed",
        error=error,
        telegram_message_id=msg_id,
    )
    await db.commit()
    if not ok:
        # Use AppError so tests get structured JSON: {error:{code,message}} with detail
        from fastapi import status as http_status

        from app.core.exceptions import AppError
        # 502: downstream (Telegram) failure, not our validation bug
        raise AppError(
            http_status.HTTP_502_BAD_GATEWAY, "TELEGRAM_FAILED", error or "Telegram send failed"
        )
    return ApiResponse(data=TelegramTestOut(ok=True, message="Test message sent"))
