import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbound_webhook import OutboundWebhook


async def list_for_team(db: AsyncSession, team_id: uuid.UUID) -> list[OutboundWebhook]:
    result = await db.execute(
        select(OutboundWebhook)
        .where(OutboundWebhook.team_id == team_id)
        .order_by(OutboundWebhook.created_at.desc())
    )
    return list(result.scalars().all())


async def list_active_for_team(db: AsyncSession, team_id: uuid.UUID) -> list[OutboundWebhook]:
    result = await db.execute(
        select(OutboundWebhook).where(
            OutboundWebhook.team_id == team_id, OutboundWebhook.is_active.is_(True)
        )
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, webhook_id: uuid.UUID) -> OutboundWebhook | None:
    return await db.get(OutboundWebhook, webhook_id)


async def create(db: AsyncSession, **fields: object) -> OutboundWebhook:
    hook = OutboundWebhook(**fields)  # type: ignore[arg-type]
    db.add(hook)
    await db.flush()
    await db.refresh(hook)
    return hook


async def delete(db: AsyncSession, hook: OutboundWebhook) -> None:
    await db.delete(hook)
    await db.flush()
