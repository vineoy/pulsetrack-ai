import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.api.deps import DBDep, MemberUser, RedisDep, client_ip
from app.core.rate_limit import check_rate_limit
from app.models.incident import IncidentStatus
from app.repositories import audit_repository, incident_repository
from app.schemas.ai import AnalysisOut
from app.schemas.common import ApiResponse
from app.schemas.incident import IncidentOut
from app.services import ai_service

router = APIRouter(prefix="/incidents", tags=["incidents"])

AI_RATE_LIMIT = 10
AI_RATE_WINDOW_SEC = 60


async def _owned_incident(db: DBDep, user: MemberUser, incident_id: uuid.UUID):
    """Tenancy guard shared by analyze/analysis/draft (404 hides other teams)."""
    from fastapi import status as http_status

    from app.core.exceptions import AppError

    incident = await incident_repository.get_by_id(db, incident_id)
    if incident is None or incident.team_id != user.team_id:
        raise AppError(http_status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Incident not found")
    return incident


async def _owned_monitor(db: DBDep, user: MemberUser, monitor_id: uuid.UUID):
    from fastapi import status as http_status

    from app.core.exceptions import AppError
    from app.models.monitor import Monitor

    monitor = await db.get(Monitor, monitor_id)
    if monitor is None or monitor.team_id != user.team_id:
        raise AppError(http_status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Monitor not found")
    return monitor


@router.get("", response_model=ApiResponse[list[IncidentOut]])
async def list_incidents(
    user: MemberUser,
    db: DBDep,
    status: Annotated[str | None, Query(pattern="^(OPEN|ACK|RESOLVED)$")] = None,
):
    rows = await incident_repository.list_for_team(db, user.team_id, status=status)
    return ApiResponse(data=[IncidentOut.model_validate(r) for r in rows])


@router.get("/export")
async def export_incidents(
    user: MemberUser,
    db: DBDep,
    status: Annotated[str | None, Query(pattern="^(OPEN|ACK|RESOLVED)$")] = None,
):
    """Download incidents as CSV (Phase 8). Streamed, team-scoped, 50k-row cap.

    Defined BEFORE /{incident_id}: "export" would otherwise hit the UUID
    converter and 422 instead of falling through.
    """
    from fastapi.responses import StreamingResponse

    from app.services import export_service

    return StreamingResponse(
        export_service.stream_incidents_csv(db, user.team_id, status),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pulsetrack-incidents.csv"},
    )


@router.get("/{incident_id}", response_model=ApiResponse[IncidentOut])
async def get_incident(user: MemberUser, incident_id: uuid.UUID, db: DBDep):
    incident = await incident_repository.get_by_id(db, incident_id)
    if incident is None or incident.team_id != user.team_id:
        from fastapi import status as http_status

        from app.core.exceptions import AppError

        raise AppError(http_status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Incident not found")
    return ApiResponse(data=IncidentOut.model_validate(incident))


@router.post("/{incident_id}/acknowledge", response_model=ApiResponse[IncidentOut])
async def acknowledge_incident(
    user: MemberUser, incident_id: uuid.UUID, request: Request, db: DBDep
):
    incident = await incident_repository.get_by_id(db, incident_id)
    if incident is None or incident.team_id != user.team_id:
        from fastapi import status as http_status

        from app.core.exceptions import AppError

        raise AppError(http_status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Incident not found")
    if incident.status != IncidentStatus.OPEN:
        from fastapi import status as http_status

        from app.core.exceptions import AppError

        raise AppError(
            http_status.HTTP_400_BAD_REQUEST,
            "INCIDENT_NOT_OPEN",
            "Only OPEN incidents can be acknowledged",
        )
    from datetime import UTC, datetime

    incident.status = IncidentStatus.ACK
    incident.ack_at = datetime.now(UTC)
    await audit_repository.log(
        db,
        action="incident.acknowledged",
        team_id=user.team_id,
        user_id=user.id,
        target_type="incident",
        target_id=str(incident.id),
        ip=client_ip(request),
    )
    await db.commit()
    await db.refresh(incident)
    return ApiResponse(data=IncidentOut.model_validate(incident))


@router.post("/{incident_id}/analyze", response_model=ApiResponse[AnalysisOut])
async def analyze_incident(
    user: MemberUser, incident_id: uuid.UUID, db: DBDep, redis: RedisDep
):
    """Explain an incident (Phase 6). Cache-first: repeat clicks cost $0."""
    await check_rate_limit(
        redis, key=f"rl:ai:{user.id}", limit=AI_RATE_LIMIT, window_sec=AI_RATE_WINDOW_SEC
    )
    incident = await _owned_incident(db, user, incident_id)
    monitor = await _owned_monitor(db, user, incident.monitor_id)
    result = await ai_service.analyze_for_incident(db, redis, incident, monitor)
    if result["summary"]:
        return ApiResponse(
            data=AnalysisOut(summary=result["summary"], cached=result["cached"])
        )
    from fastapi import status as http_status

    from app.core.exceptions import AppError

    error = result["error"] or "AI failed to analyze — retry shortly"
    if "not configured" in error:
        raise AppError(http_status.HTTP_503_SERVICE_UNAVAILABLE, "AI_NOT_CONFIGURED", error)
    raise AppError(http_status.HTTP_502_BAD_GATEWAY, "AI_FAILED", error)


@router.get("/{incident_id}/analysis", response_model=ApiResponse[AnalysisOut])
async def get_analysis(user: MemberUser, incident_id: uuid.UUID, db: DBDep, redis: RedisDep):
    """Cached read only (~50ms, $0, zero Gemini calls)."""
    incident = await _owned_incident(db, user, incident_id)
    hit = await ai_service.cache_get(redis, ai_service.analysis_key(incident.id))
    if hit:
        return ApiResponse(data=AnalysisOut(summary=hit, cached=True))
    if incident.ai_summary:
        await ai_service.cache_set(redis, ai_service.analysis_key(incident.id), incident.ai_summary)
        return ApiResponse(data=AnalysisOut(summary=incident.ai_summary, cached=True))
    from fastapi import status as http_status

    from app.core.exceptions import AppError

    raise AppError(
        http_status.HTTP_404_NOT_FOUND, "AI_NO_ANALYSIS", "No analysis yet — POST analyze first"
    )


@router.get("/by-monitor/{monitor_id}", response_model=ApiResponse[list[IncidentOut]])
async def list_for_monitor(user: MemberUser, monitor_id: uuid.UUID, db: DBDep):
    # Tenancy guard via monitor lookup
    from app.models.monitor import Monitor

    monitor = await db.get(Monitor, monitor_id)
    if monitor is None or monitor.team_id != user.team_id:
        from fastapi import status as http_status

        from app.core.exceptions import AppError

        raise AppError(http_status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Monitor not found")
    rows = await incident_repository.list_for_monitor(db, monitor_id)
    return ApiResponse(data=[IncidentOut.model_validate(r) for r in rows])
