import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.maintenance_window import MaintenanceWindow


async def list_for_team(
    db: AsyncSession, team_id: uuid.UUID
) -> list[MaintenanceWindow]:
    result = await db.execute(
        select(MaintenanceWindow)
        .where(MaintenanceWindow.team_id == team_id)
        .order_by(MaintenanceWindow.starts_at.desc())
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, window_id: uuid.UUID) -> MaintenanceWindow | None:
    return await db.get(MaintenanceWindow, window_id)


async def find_active_for_monitor(
    db: AsyncSession, team_id: uuid.UUID, monitor_id: uuid.UUID, now: datetime
) -> MaintenanceWindow | None:
    result = await db.execute(
        select(MaintenanceWindow).where(
            MaintenanceWindow.team_id == team_id,
            MaintenanceWindow.starts_at <= now,
            MaintenanceWindow.ends_at >= now,
            ((MaintenanceWindow.monitor_id.is_(None))
             | (MaintenanceWindow.monitor_id == monitor_id)),
        )
        .order_by(MaintenanceWindow.ends_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    team_id: uuid.UUID,
    monitor_id: uuid.UUID | None,
    starts_at: datetime,
    ends_at: datetime,
    reason: str | None,
    created_by: uuid.UUID | None,
) -> MaintenanceWindow:
    window = MaintenanceWindow(
        team_id=team_id,
        monitor_id=monitor_id,
        starts_at=starts_at,
        ends_at=ends_at,
        reason=reason,
        created_by=created_by,
    )
    db.add(window)
    await db.flush()
    await db.refresh(window)
    return window


async def delete(db: AsyncSession, window: MaintenanceWindow) -> None:
    await db.delete(window)
    await db.flush()
