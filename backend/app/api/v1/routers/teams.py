import uuid

from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser, DBDep, OwnerUser, client_ip
from app.schemas.auth import UserOut
from app.schemas.common import ApiResponse
from app.schemas.team import InviteIn, InviteOut, TeamDetailOut, TeamUpdateIn
from app.services import team_service

router = APIRouter(prefix="/teams", tags=["teams"])


async def _team_detail(user: CurrentUser, db: DBDep) -> TeamDetailOut:
    team, count = await team_service.get_team_with_member_count(db, user)
    return TeamDetailOut(
        id=team.id,
        name=team.name,
        slug=team.slug,
        plan=team.plan.value,
        created_at=team.created_at,
        members_count=count,
    )


@router.get("/me", response_model=ApiResponse[TeamDetailOut])
async def my_team(user: CurrentUser, db: DBDep):
    return ApiResponse(data=await _team_detail(user, db))


@router.put("/me", response_model=ApiResponse[TeamDetailOut])
async def update_my_team(user: OwnerUser, body: TeamUpdateIn, request: Request, db: DBDep):
    await team_service.update_team(db, user, body, client_ip(request))
    return ApiResponse(data=await _team_detail(user, db))


@router.get("/members", response_model=ApiResponse[list[UserOut]])
async def members(user: CurrentUser, db: DBDep):
    members = await team_service.list_members(db, user)
    return ApiResponse(data=[UserOut.model_validate(member) for member in members])


@router.post("/invite", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[InviteOut])
async def invite(user: OwnerUser, body: InviteIn, request: Request, db: DBDep):
    invited, temp_password = await team_service.invite_member(db, user, body, client_ip(request))
    return ApiResponse(
        data=InviteOut(user=UserOut.model_validate(invited), temp_password=temp_password)
    )


@router.delete("/members/{member_id}", response_model=ApiResponse[dict])
async def remove_member(
    user: OwnerUser, member_id: uuid.UUID, request: Request, db: DBDep
):
    """Remove a member/viewer from the team. Instant login death, data untouched."""
    from app.core.exceptions import AppError
    from app.repositories import audit_repository, user_repository

    if member_id == user.id:
        raise AppError(400, "CANNOT_REMOVE_SELF", "You cannot remove yourself")
    target = await user_repository.get_by_id(db, member_id)
    if target is None or target.team_id != user.team_id:
        raise AppError(404, "NOT_FOUND", "Member not found")
    await audit_repository.log(
        db,
        action="team.member_removed",
        team_id=user.team_id,
        user_id=user.id,
        target_type="user",
        target_id=str(target.id),
        detail={"email": target.email, "role": target.role.value},
        ip=client_ip(request),
    )
    await db.delete(target)
    await db.commit()
    return ApiResponse(data={"deleted": True})
