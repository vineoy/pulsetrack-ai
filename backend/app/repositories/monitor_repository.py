import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.check import Check
from app.models.monitor import Monitor


async def get_by_id(db: AsyncSession, monitor_id: uuid.UUID) -> Monitor | None:
    return await db.get(Monitor, monitor_id)


async def list_for_team(db: AsyncSession, team_id: uuid.UUID) -> list[Monitor]:
    result = await db.execute(
        select(Monitor).where(Monitor.team_id == team_id).order_by(Monitor.created_at.desc())
    )
    return list(result.scalars().all())


async def count_for_team(db: AsyncSession, team_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(Monitor).where(Monitor.team_id == team_id)
    )
    return int(result.scalar_one())


async def create(db: AsyncSession, **fields: object) -> Monitor:
    monitor = Monitor(**fields)  # type: ignore[arg-type]
    db.add(monitor)
    await db.flush()
    await db.refresh(monitor)
    return monitor


async def stats(
    db: AsyncSession, monitor_id: uuid.UUID, days: int
) -> dict[str, object]:
    since = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(Check.status == "UP").label("up"),
            func.count().filter(Check.status == "DOWN").label("down"),
            func.avg(Check.latency_ms).label("avg_latency"),
            func.percentile_cont(0.5).within_group(Check.latency_ms).label("p50"),
            func.percentile_cont(0.95).within_group(Check.latency_ms).label("p95"),
            func.max(Check.checked_at).label("last_checked_at"),
        ).where(Check.monitor_id == monitor_id, Check.checked_at >= since)
    )
    row = result.one()
    return dict(row._mapping)  # noqa: SLF001 - Row._mapping is the public-ish accessor
