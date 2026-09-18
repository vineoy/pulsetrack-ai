import uuid

from fastapi import APIRouter, Request, status

from app.api.deps import DBDep, MemberUser, client_ip
from app.models.monitor import Monitor
from app.repositories import audit_repository, maintenance_repository
from app.schemas.common import ApiResponse
from app.schemas.maintenance import MaintenanceIn, MaintenanceOut

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.get("", response_model=ApiResponse[list[MaintenanceOut]])
async def list_windows(user: MemberUser, db: DBDep):
    rows = await maintenance_repository.list_for_team(db, user.team_id)
    return ApiResponse(data=[MaintenanceOut.model_validate(r) for r in rows])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[MaintenanceOut])
async def create_window(
    user: MemberUser, body: MaintenanceIn, request: Request, db: DBDep
):
    # If monitor_id is set, ensure it belongs to this team (no leak)
    if body.monitor_id is not None:
        monitor = await db.get(Monitor, body.monitor_id)
        if monitor is None or monitor.team_id != user.team_id:
            from fastapi import status as http_status

            from app.core.exceptions import AppError

            raise AppError(http_status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Monitor not found")
    window = await maintenance_repository.create(
        db,
        team_id=user.team_id,
        monitor_id=body.monitor_id,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        reason=body.reason,
        created_by=user.id,
    )
    await audit_repository.log(
        db,
        action="maintenance.created",
        team_id=user.team_id,
        user_id=user.id,
        target_type="maintenance_window",
        target_id=str(window.id),
        detail={
            "monitor_id": str(body.monitor_id) if body.monitor_id else None,
            "reason": body.reason,
        },
        ip=client_ip(request),
    )
    await db.commit()
    return ApiResponse(data=MaintenanceOut.model_validate(window))


@router.delete("/{window_id}", response_model=ApiResponse[dict])
async def delete_window(
    user: MemberUser, window_id: uuid.UUID, request: Request, db: DBDep
):
    window = await maintenance_repository.get_by_id(db, window_id)
    if window is None or window.team_id != user.team_id:
        from fastapi import status as http_status

        from app.core.exceptions import AppError

        raise AppError(http_status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Maintenance window not found")
    await audit_repository.log(
        db,
        action="maintenance.deleted",
        team_id=user.team_id,
        user_id=user.id,
        target_type="maintenance_window",
        target_id=str(window.id),
        ip=client_ip(request),
    )
    await maintenance_repository.delete(db, window)
    await db.commit()
    return ApiResponse(data={"deleted": True})
