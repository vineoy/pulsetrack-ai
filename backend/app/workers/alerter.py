"""ARQ jobs for Telegram alerts. Enqueued by checker.py or the API.

Design: API/worker never calls Telegram inline in the request path beyond
enqueuing a job. The job does the maintenance gate, the send, the logging,
and the escalation scheduling. Retries happen inside telegram_service (3x).
"""

import uuid
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.db import async_session_factory
from app.models.incident import Incident
from app.models.monitor import Monitor
from app.services import alert_service


async def telegram_alert_job(ctx: dict, incident_id: str, kind: str) -> str:
    """Generic alert job: kind = open|recovery|escalation. Called by checker."""
    iid = uuid.UUID(incident_id)
    async with async_session_factory() as db:
        incident = await db.get(Incident, iid)
        if incident is None:
            return "skipped:incident_gone"
        monitor = await db.get(Monitor, incident.monitor_id)
        if monitor is None:
            return "skipped:monitor_gone"

        # Deduplicate escalation: only once per incident
        if kind == "escalation" and not alert_service.should_escalate(incident):
            return "skipped:not_escalatable"

        results = await alert_service.send_for_incident(db, incident, monitor, kind)

        # After a successful OPEN, schedule escalation 10 min later (defer)
        if kind == "open":
            delay_min = get_settings().telegram_escalation_delay_min
            # Check if any result was actually sent (not skipped)
            if any(r["status"] == "sent" for r in results):
                try:
                    # ARQ _defer_by is seconds
                    await ctx["redis"].enqueue_job(
                        "telegram_alert_job", incident_id, "escalation", _defer_by=delay_min * 60
                    )
                except Exception:
                    pass
                return f"open sent, escalation scheduled in {delay_min}m"
            # Even if skipped (no channel / maintenance) we still return
            return f"open {results[0]['status'] if results else 'no_results'}"

        if kind == "escalation" and any(r["status"] == "sent" for r in results):
            incident.escalated_at = datetime.now(UTC)
            await db.commit()
            return "escalated"

        count_sent = sum(1 for r in results if r["status"] == "sent")
        return f"{kind} done sent={count_sent}/{len(results)}"


async def telegram_test_job(ctx: dict, channel_id: str) -> str:
    """Test job: called from the API Test button (enqueued for consistency)."""
    cid = uuid.UUID(channel_id)
    from app.repositories import notification_channel_repository

    async with async_session_factory() as db:
        channel = await notification_channel_repository.get_by_id(db, cid)
        if channel is None:
            return "skipped:channel_gone"
        # Try to pick any monitor for richer test message
        monitor = None
        from sqlalchemy import select

        from app.models.monitor import Monitor

        result = await db.execute(
            select(Monitor).where(Monitor.team_id == channel.team_id).limit(1)
        )
        monitor = result.scalar_one_or_none()
        ok, error = await alert_service.send_test_for_channel(db, channel, monitor)
        return "sent" if ok else f"failed: {error}"


async def sweep_stale_escalations(ctx: dict) -> int:
    """Cron fallback: if Redis defer was lost, find OPEN 10m+ unacked and escalate.

    Runs every minute; harmless if nothing to do. Keeps escalation reliable on free tier
    where
    the worker may sleep.
    """
    from datetime import timedelta

    from sqlalchemy import select

    delay_min = get_settings().telegram_escalation_delay_min
    cutoff = datetime.now(UTC) - timedelta(minutes=delay_min)
    async with async_session_factory() as db:
        result = await db.execute(
            select(Incident).where(
                Incident.status == "OPEN",
                Incident.ack_at.is_(None),
                Incident.escalated_at.is_(None),
                Incident.started_at <= cutoff,
            )
        )
        incidents = list(result.scalars().all())
        count = 0
        for incident in incidents:
            # Check maintenance before enqueuing
            monitor = await db.get(Monitor, incident.monitor_id)
            if monitor and await alert_service.is_in_maintenance(
                db, incident.team_id, monitor.id
            ):
                continue
            try:
                await ctx["redis"].enqueue_job(
                    "telegram_alert_job", str(incident.id), "escalation"
                )
                count += 1
            except Exception:
                pass
        return count
