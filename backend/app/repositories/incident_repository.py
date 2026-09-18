import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentStatus


async def get_by_id(db: AsyncSession, incident_id: uuid.UUID) -> Incident | None:
    return await db.get(Incident, incident_id)


async def list_for_team(
    db: AsyncSession, team_id: uuid.UUID, status: str | None = None
) -> list[Incident]:
    query = select(Incident).where(Incident.team_id == team_id)
    if status:
        query = query.where(Incident.status == status)
    query = query.order_by(Incident.started_at.desc()).limit(100)
    result = await db.execute(query)
    return list(result.scalars().all())


async def page_for_team(
    db: AsyncSession,
    team_id: uuid.UUID,
    *,
    status: str | None = None,
    offset: int = 0,
    limit: int = 2000,
) -> list[Incident]:
    """Chunked reader for CSV export (newest first). No cap here — caller caps."""
    query = select(Incident).where(Incident.team_id == team_id)
    if status:
        query = query.where(Incident.status == status)
    result = await db.execute(
        query.order_by(Incident.started_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


async def list_for_monitor(
    db: AsyncSession, monitor_id: uuid.UUID
) -> list[Incident]:
    result = await db.execute(
        select(Incident)
        .where(Incident.monitor_id == monitor_id)
        .order_by(Incident.started_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


async def get_open_for_monitor(
    db: AsyncSession, monitor_id: uuid.UUID
) -> Incident | None:
    result = await db.execute(
        select(Incident)
        .where(Incident.monitor_id == monitor_id, Incident.status == IncidentStatus.OPEN)
        .order_by(Incident.started_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
