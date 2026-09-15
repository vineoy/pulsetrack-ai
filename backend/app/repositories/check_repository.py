import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.check import Check


async def create(db: AsyncSession, **fields: object) -> Check:
    check = Check(**fields)  # type: ignore[arg-type]
    db.add(check)
    await db.flush()
    return check


async def page_for_monitor(
    db: AsyncSession,
    monitor_id: uuid.UUID,
    *,
    page: int,
    limit: int,
    time_from: datetime | None,
    time_to: datetime | None,
) -> tuple[list[Check], int]:
    query = select(Check).where(Check.monitor_id == monitor_id)
    count_query = (
        select(func.count()).select_from(Check).where(Check.monitor_id == monitor_id)
    )
    if time_from is not None:
        query = query.where(Check.checked_at >= time_from)
        count_query = count_query.where(Check.checked_at >= time_from)
    if time_to is not None:
        query = query.where(Check.checked_at <= time_to)
        count_query = count_query.where(Check.checked_at <= time_to)

    total = int((await db.execute(count_query)).scalar_one())
    rows = await db.execute(
        query.order_by(Check.checked_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    return list(rows.scalars().all()), total


async def last_check(db: AsyncSession, monitor_id: uuid.UUID) -> Check | None:
    result = await db.execute(
        select(Check)
        .where(Check.monitor_id == monitor_id)
        .order_by(Check.checked_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def recent_for_monitor(db: AsyncSession, monitor_id: uuid.UUID, limit: int) -> list[Check]:
    result = await db.execute(
        select(Check)
        .where(Check.monitor_id == monitor_id)
        .order_by(Check.checked_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def latest_per_monitor(
    db: AsyncSession, monitor_ids: list[uuid.UUID]
) -> dict[uuid.UUID, Check]:
    """One DISTINCT ON query for the whole dashboard list — not N+1 per monitor."""
    if not monitor_ids:
        return {}
    result = await db.execute(
        select(Check)
        .where(Check.monitor_id.in_(monitor_ids))
        .distinct(Check.monitor_id)  # PostgreSQL DISTINCT ON: newest check per monitor
        .order_by(Check.monitor_id, Check.checked_at.desc())
    )
    return {check.monitor_id: check for check in result.scalars().all()}
