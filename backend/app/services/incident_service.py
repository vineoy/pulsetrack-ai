import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.check import Check
from app.models.incident import Incident, IncidentStatus
from app.models.monitor import Monitor


async def get_open_incident(db: AsyncSession, monitor_id: uuid.UUID) -> Incident | None:
    result = await db.execute(
        select(Incident)
        .where(Incident.monitor_id == monitor_id, Incident.status == IncidentStatus.OPEN)
        .order_by(Incident.started_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _last_two_checks(db: AsyncSession, monitor_id: uuid.UUID) -> list[Check]:
    result = await db.execute(
        select(Check)
        .where(Check.monitor_id == monitor_id)
        .order_by(Check.checked_at.desc())
        .limit(2)
    )
    return list(result.scalars().all())


async def apply_flap_logic(db: AsyncSession, monitor: Monitor) -> Incident | None:
    """Decide incident state from the two most recent checks (roadmap flap rule).

    - 2 consecutive DOWN + no OPEN incident  -> create OPEN (returns the new incident)
    - 2 consecutive UP  + an OPEN incident   -> RESOLVE it (downtime computed)
    - anything else                          -> no change (returns None)

    Idempotent: running it twice after the same checks cannot create two incidents.
    """
    checks = await _last_two_checks(db, monitor.id)
    if len(checks) < 2:
        return None

    last, previous = checks[0], checks[1]

    if previous.status == "DOWN" and last.status == "DOWN":
        if await get_open_incident(db, monitor.id) is None:
            incident = Incident(
                monitor_id=monitor.id,
                team_id=monitor.team_id,
                status=IncidentStatus.OPEN,
                started_at=last.checked_at,
            )
            db.add(incident)
            await db.flush()
            return incident
        return None

    if previous.status == "UP" and last.status == "UP":
        open_incident = await get_open_incident(db, monitor.id)
        if open_incident is not None:
            resolved_at = datetime.now(UTC)
            open_incident.status = IncidentStatus.RESOLVED
            open_incident.resolved_at = resolved_at
            open_incident.downtime_sec = max(
                0, int((resolved_at - open_incident.started_at).total_seconds())
            )
            await db.flush()
            return open_incident
    return None
