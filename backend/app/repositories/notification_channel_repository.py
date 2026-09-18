import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_channel import NotificationChannel


async def list_for_team(db: AsyncSession, team_id: uuid.UUID) -> list[NotificationChannel]:
    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.team_id == team_id)
        .order_by(NotificationChannel.created_at.desc())
    )
    return list(result.scalars().all())


async def list_active_for_team(
    db: AsyncSession, team_id: uuid.UUID
) -> list[NotificationChannel]:
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.team_id == team_id, NotificationChannel.is_active.is_(True)
        )
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, channel_id: uuid.UUID) -> NotificationChannel | None:
    return await db.get(NotificationChannel, channel_id)


async def find_by_chat_id(
    db: AsyncSession, team_id: uuid.UUID, telegram_chat_id: str
) -> NotificationChannel | None:
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.team_id == team_id,
            NotificationChannel.telegram_chat_id == telegram_chat_id,
        )
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    team_id: uuid.UUID,
    telegram_chat_id: str,
    label: str | None = None,
) -> NotificationChannel:
    channel = NotificationChannel(
        team_id=team_id, type="telegram", telegram_chat_id=telegram_chat_id, label=label
    )
    db.add(channel)
    await db.flush()
    await db.refresh(channel)
    return channel


async def delete(db: AsyncSession, channel: NotificationChannel) -> None:
    await db.delete(channel)
    await db.flush()
