import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team
from app.models.user import User


async def get_by_slug(db: AsyncSession, slug: str) -> Team | None:
    result = await db.execute(select(Team).where(Team.slug == slug))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, team_id: uuid.UUID) -> Team | None:
    return await db.get(Team, team_id)


async def create(db: AsyncSession, **fields: object) -> Team:
    team = Team(**fields)  # type: ignore[arg-type]
    db.add(team)
    await db.flush()
    await db.refresh(team)
    return team


async def count_members(db: AsyncSession, team_id: uuid.UUID) -> int:
    result = await db.execute(select(func.count()).select_from(User).where(User.team_id == team_id))
    return int(result.scalar_one())


async def list_members(db: AsyncSession, team_id: uuid.UUID) -> list[User]:
    result = await db.execute(
        select(User).where(User.team_id == team_id).order_by(User.created_at)
    )
    return list(result.scalars().all())
