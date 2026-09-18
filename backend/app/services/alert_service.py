"""Alert orchestration: maintenance gate → Telegram send → alert_logs → escalation scheduling."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentStatus
from app.models.monitor import Monitor
from app.repositories import (
    alert_log_repository,
    maintenance_repository,
    notification_channel_repository,
)
from app.services import telegram_service


async def is_in_maintenance(
    db: AsyncSession, team_id: uuid.UUID, monitor_id: uuid.UUID
) -> bool:
    now = datetime.now(UTC)
    window = await maintenance_repository.find_active_for_monitor(db, team_id, monitor_id, now)
    return window is not None


async def send_for_incident(
    db: AsyncSession,
    incident: Incident,
    monitor: Monitor,
    kind: str,
) -> list[dict]:
    """Send Telegram for one incident. Returns per-channel results. Handles maintenance skip."""
    team_id = incident.team_id
    # kind: open | recovery | escalation | test (incident needed for first three)
    if await is_in_maintenance(db, team_id, monitor.id):
        await alert_log_repository.create(
            db,
            team_id=team_id,
            incident_id=incident.id if incident else None,
            channel_id=None,
            monitor_id=monitor.id,
            kind=kind,
            status="skipped",
            error="in maintenance window",
        )
        await db.commit()
        return [{"status": "skipped", "reason": "maintenance"}]

    channels = await notification_channel_repository.list_active_for_team(db, team_id)
    if not channels:
        await alert_log_repository.create(
            db,
            team_id=team_id,
            incident_id=incident.id if incident else None,
            channel_id=None,
            monitor_id=monitor.id,
            kind=kind,
            status="skipped",
            error="no active telegram channel",
        )
        await db.commit()
        return [{"status": "skipped", "reason": "no_channel"}]

    # Build text once
    if kind == "open":
        text = telegram_service.build_open_message(monitor.name, monitor.url, str(incident.id))
    elif kind == "recovery":
        downtime_min = max(0, (incident.downtime_sec or 0) // 60)
        text = telegram_service.build_recovery_message(monitor.name, monitor.url, downtime_min)
    elif kind == "escalation":
        text = telegram_service.build_escalation_message(
            monitor.name, monitor.url, str(incident.id)
        )
    else:
        text = telegram_service.build_test_message(monitor.name)

    results: list[dict] = []
    for channel in channels:
        ok, error, msg_id = await telegram_service.send_message(channel.telegram_chat_id, text)
        status = "sent" if ok else "failed"
        await alert_log_repository.create(
            db,
            team_id=team_id,
            incident_id=incident.id if incident else None,
            channel_id=channel.id,
            monitor_id=monitor.id,
            kind=kind,
            status=status,
            attempts=telegram_service.MAX_RETRIES if not ok else 1,
            error=error,
            telegram_message_id=msg_id,
        )
        results.append({"channel_id": str(channel.id), "status": status, "error": error})

    await db.commit()
    return results


async def send_test_for_channel(
    db: AsyncSession, channel, monitor: Monitor | None
) -> tuple[bool, str | None]:
    """Send a test message to one channel. Used by the Test button."""
    if await is_in_maintenance(db, channel.team_id, monitor.id) if monitor else False:
        return False, "In maintenance window — alerts are muted (test blocked)"
    text = telegram_service.build_test_message(monitor.name if monitor else None)
    ok, error, msg_id = await telegram_service.send_message(channel.telegram_chat_id, text)
    await alert_log_repository.create(
        db,
        team_id=channel.team_id,
        incident_id=None,
        channel_id=channel.id,
        monitor_id=monitor.id if monitor else None,
        kind="test",
        status="sent" if ok else "failed",
        error=error,
        telegram_message_id=msg_id,
    )
    await db.commit()
    return ok, error


def should_escalate(incident: Incident) -> bool:
    return (
        incident.status == IncidentStatus.OPEN
        and incident.ack_at is None
        and incident.escalated_at is None
    )
