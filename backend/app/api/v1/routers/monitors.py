import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, Request, status

from app.api.deps import DBDep, MemberUser, OwnerUser, client_ip
from app.schemas.common import ApiResponse
from app.schemas.monitor import (
    CheckOut,
    CheckPage,
    MonitorIn,
    MonitorOut,
    MonitorSummaryOut,
    MonitorUpdateIn,
    StatsOut,
)
from app.services import monitor_service

router = APIRouter(prefix="/monitors", tags=["monitors"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[MonitorOut])
async def create_monitor(user: MemberUser, body: MonitorIn, request: Request, db: DBDep):
    monitor = await monitor_service.create_monitor(db, user, body, client_ip(request))
    return ApiResponse(data=MonitorOut.model_validate(monitor))


@router.get("", response_model=ApiResponse[list[MonitorSummaryOut]])
async def list_monitors(user: MemberUser, db: DBDep):
    rows = await monitor_service.list_monitors(db, user)
    return ApiResponse(data=[MonitorSummaryOut(**row) for row in rows])  # type: ignore[arg-type]


@router.get("/{monitor_id}", response_model=ApiResponse[dict])
async def get_monitor(user: MemberUser, monitor_id: uuid.UUID, db: DBDep):
    detail = await monitor_service.get_monitor_detail(db, user, monitor_id)
    checks = [CheckOut.model_validate(check) for check in detail["last_20_checks"]]  # type: ignore[arg-type]
    monitor = MonitorOut.model_validate(detail["monitor"])  # type: ignore[arg-type]
    return ApiResponse(
        data={
            **monitor.model_dump(),
            "uptime_pct_30d": detail["uptime_pct_30d"],
            "last_20_checks": [check.model_dump() for check in checks],
        }
    )


@router.put("/{monitor_id}", response_model=ApiResponse[MonitorOut])
async def update_monitor(
    user: MemberUser, monitor_id: uuid.UUID, body: MonitorUpdateIn, request: Request, db: DBDep
):
    monitor = await monitor_service.update_monitor(db, user, monitor_id, body, client_ip(request))
    return ApiResponse(data=MonitorOut.model_validate(monitor))


@router.delete("/{monitor_id}", response_model=ApiResponse[dict])
async def delete_monitor(user: OwnerUser, monitor_id: uuid.UUID, request: Request, db: DBDep):
    await monitor_service.delete_monitor(db, user, monitor_id, client_ip(request))
    return ApiResponse(data={"deleted": True})


@router.post("/{monitor_id}/pause", response_model=ApiResponse[MonitorOut])
async def pause_monitor(user: MemberUser, monitor_id: uuid.UUID, request: Request, db: DBDep):
    monitor = await monitor_service.set_paused(db, user, monitor_id, True, client_ip(request))
    return ApiResponse(data=MonitorOut.model_validate(monitor))


@router.post("/{monitor_id}/resume", response_model=ApiResponse[MonitorOut])
async def resume_monitor(user: MemberUser, monitor_id: uuid.UUID, request: Request, db: DBDep):
    monitor = await monitor_service.set_paused(db, user, monitor_id, False, client_ip(request))
    return ApiResponse(data=MonitorOut.model_validate(monitor))


@router.get("/{monitor_id}/checks", response_model=ApiResponse[CheckPage])
async def list_checks(
    user: MemberUser,
    monitor_id: uuid.UUID,
    db: DBDep,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    time_from: Annotated[datetime | None, Query(alias="from")] = None,
    time_to: Annotated[datetime | None, Query(alias="to")] = None,
):
    check_page = await monitor_service.get_checks_page(
        db, user, monitor_id, page=page, limit=limit, time_from=time_from, time_to=time_to
    )
    check_page.items = [CheckOut.model_validate(check) for check in check_page.items]  # type: ignore[misc]
    return ApiResponse(data=check_page)


@router.get("/{monitor_id}/checks/export")
async def export_checks(
    user: MemberUser,
    monitor_id: uuid.UUID,
    db: DBDep,
    time_from: Annotated[datetime | None, Query(alias="from")] = None,
    time_to: Annotated[datetime | None, Query(alias="to")] = None,
):
    """Download checks as CSV (Phase 8). Streamed, team-scoped, 50k-row cap."""
    from fastapi.responses import StreamingResponse

    from app.repositories import monitor_repository
    from app.services import export_service

    monitor = await monitor_repository.get_by_id(db, monitor_id)
    if monitor is None or monitor.team_id != user.team_id:
        from fastapi import status as http_status

        from app.core.exceptions import AppError

        raise AppError(http_status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Monitor not found")
    short_id = str(monitor.id)[:8]
    return StreamingResponse(
        export_service.stream_checks_csv(db, monitor.id, time_from, time_to),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=pulsetrack-checks-{short_id}.csv"},
    )


@router.get("/{monitor_id}/stats", response_model=ApiResponse[StatsOut])
async def get_stats(
    user: MemberUser,
    monitor_id: uuid.UUID,
    db: DBDep,
    days: Annotated[int, Query(ge=1, le=90)] = 30,
):
    return ApiResponse(data=await monitor_service.get_stats(db, user, monitor_id, days))
