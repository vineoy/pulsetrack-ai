"""Immutable audit trail reader (Phase 7).

GET /audit-logs  Owner  ?user=&action=&page=&limit= — newest first.
Rows are INSERT-only across the app; no update/delete endpoint exists by design.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import DBDep, OwnerUser
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogOut, AuditPage
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=ApiResponse[AuditPage])
async def list_audit_logs(
    user: OwnerUser,
    db: DBDep,
    action: Annotated[str | None, Query(max_length=100)] = None,
    user_id: Annotated[uuid.UUID | None, Query(alias="user")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    query = select(AuditLog).where(AuditLog.team_id == user.team_id)
    count_query = (
        select(func.count()).select_from(AuditLog).where(AuditLog.team_id == user.team_id)
    )
    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
        count_query = count_query.where(AuditLog.user_id == user_id)
    total = int((await db.execute(count_query)).scalar_one())
    rows = await db.execute(
        query.order_by(AuditLog.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    items = list(rows.scalars().all())
    return ApiResponse(
        data=AuditPage(
            items=[AuditLogOut.model_validate(r) for r in items],
            total=total,
            page=page,
            limit=limit,
        )
    )
