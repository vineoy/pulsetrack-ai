import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.heartbeat import Heartbeat


async def list_for_team(db: AsyncSession, team_id: uuid.UUID) -> list[Heartbeat]:
    result = await db.execute(
        select(Heartbeat).where(Heartbeat.team_id == team_id).order_by(Heartbeat.created_at.desc())
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, heartbeat_id: uuid.UUID) -> Heartbeat | None:
    return await db.get(Heartbeat, heartbeat_id)


async def get_by_key(db: AsyncSession, ping_key: str) -> Heartbeat | None:
    result = await db.execute(select(Heartbeat).where(Heartbeat.ping_key == ping_key))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, **fields: object) -> Heartbeat:
    hb = Heartbeat(**fields)  # type: ignore[arg-type]
    db.add(hb)
    await db.flush()
    await db.refresh(hb)
    return hb


async def delete(db: AsyncSession, hb: Heartbeat) -> None:
    await db.delete(hb)
    await db.flush()
