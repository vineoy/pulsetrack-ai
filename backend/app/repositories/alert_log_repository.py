import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_log import AlertLog


async def create(
    db: AsyncSession,
    *,
    team_id: uuid.UUID,
    incident_id: uuid.UUID | None,
    channel_id: uuid.UUID | None,
    monitor_id: uuid.UUID | None,
    kind: str,
    status: str,
    attempts: int = 1,
    error: str | None = None,
    telegram_message_id: int | None = None,
) -> AlertLog:
    log = AlertLog(
        team_id=team_id,
        incident_id=incident_id,
        channel_id=channel_id,
        monitor_id=monitor_id,
        kind=kind,
        status=status,
        attempts=attempts,
        error=error,
        telegram_message_id=telegram_message_id,
    )
    db.add(log)
    await db.flush()
    return log
