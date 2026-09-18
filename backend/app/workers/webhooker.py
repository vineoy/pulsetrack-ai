"""Outbound webhook delivery job (Phase 7).

Enqueued next to the Telegram alert whenever an incident OPENs or RECOVERs.
Per active team URL: signed POST (HMAC, 3× retry inside webhook_service),
one audit_logs row per URL as the delivery receipt. Never raises.
"""

from __future__ import annotations

import uuid

from app.core.db import async_session_factory
from app.models.monitor import Monitor
from app.models.team import Team
from app.repositories import audit_repository, incident_repository, webhook_repository
from app.services import webhook_service


async def webhook_delivery_job(ctx: dict, incident_id: str, kind: str) -> str:
    """kind: open | recovery. Maps to events incident.opened / incident.resolved."""
    try:
        iid = uuid.UUID(incident_id)
    except ValueError:
        return "skipped:bad_id"
    event = "incident.opened" if kind == "open" else "incident.resolved"
    async with async_session_factory() as db:
        incident = await incident_repository.get_by_id(db, iid)
        if incident is None:
            return "skipped:incident_gone"
        monitor = await db.get(Monitor, incident.monitor_id)
        if monitor is None:
            return "skipped:monitor_gone"
        team = await db.get(Team, incident.team_id)
        hooks = await webhook_repository.list_active_for_team(db, incident.team_id)
        if not hooks:
            return "skipped:no_webhook"
        payload = webhook_service.build_event(
            event,
            team_slug=team.slug if team else "team",
            monitor_name=monitor.name,
            monitor_url=monitor.url,
            incident={
                "id": str(incident.id),
                "status": incident.status,
                "started_at": incident.started_at.isoformat() if incident.started_at else None,
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                "downtime_sec": incident.downtime_sec,
            },
        )
        sent = 0
        for hook in hooks:
            ok, error, status_code = await webhook_service.deliver(hook.url, hook.secret, payload)
            await audit_repository.log(
                db,
                action="webhook.delivered" if ok else "webhook.failed",
                team_id=incident.team_id,
                target_type="outbound_webhook",
                target_id=str(hook.id),
                detail={
                    "event": event,
                    "incident_id": str(incident.id),
                    "status_code": status_code,
                    "error": error,
                },
            )
            sent += 1 if ok else 0
        await db.commit()
        return f"{kind} delivered={sent}/{len(hooks)}"
