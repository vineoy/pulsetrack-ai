"""Machine credentials for scripts/CI (Phase 7).

POST   /api-keys      Owner  mint key, raw value shown ONCE (`pk_live_...`)
GET    /api-keys      Owner  list prefixes (never raw values)
DELETE /api-keys/{id} Owner  revoke (instant 401 afterwards)

Keys work anywhere JWT does: `Authorization: Bearer pk_live_...`.
They inherit the creator's role and die with deactivation (see api.deps).
"""

import uuid

from fastapi import APIRouter, Request, status

from app.api.deps import DBDep, OwnerUser, client_ip
from app.core.exceptions import AppError
from app.repositories import api_key_repository, audit_repository
from app.schemas.api_key import ApiKeyCreatedOut, ApiKeyIn, ApiKeyOut
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[ApiKeyCreatedOut])
async def create_key(user: OwnerUser, body: ApiKeyIn, request: Request, db: DBDep):
    row, raw = await api_key_repository.create(
        db, team_id=user.team_id, user_id=user.id, name=body.name.strip()
    )
    await audit_repository.log(
        db,
        action="api_key.created",
        team_id=user.team_id,
        user_id=user.id,
        target_type="api_key",
        target_id=str(row.id),
        detail={"name": row.name, "prefix": row.prefix},
        ip=client_ip(request),
    )
    await db.commit()
    return ApiResponse(
        data=ApiKeyCreatedOut(
            id=row.id,
            team_id=row.team_id,
            name=row.name,
            prefix=row.prefix,
            created_at=row.created_at,
            key=raw,
        )
    )


@router.get("", response_model=ApiResponse[list[ApiKeyOut]])
async def list_keys(user: OwnerUser, db: DBDep):
    rows = await api_key_repository.list_for_team(db, user.team_id)
    return ApiResponse(data=[ApiKeyOut.model_validate(r) for r in rows])


@router.delete("/{key_id}", response_model=ApiResponse[dict])
async def revoke_key(user: OwnerUser, key_id: uuid.UUID, request: Request, db: DBDep):
    row = await api_key_repository.get_by_id(db, key_id)
    if row is None or row.team_id != user.team_id:
        raise AppError(404, "NOT_FOUND", "API key not found")
    await audit_repository.log(
        db,
        action="api_key.deleted",
        team_id=user.team_id,
        user_id=user.id,
        target_type="api_key",
        target_id=str(row.id),
        detail={"name": row.name, "prefix": row.prefix},
        ip=client_ip(request),
    )
    await api_key_repository.delete(db, row)
    await db.commit()
    return ApiResponse(data={"deleted": True})
