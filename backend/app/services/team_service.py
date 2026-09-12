import re
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.team import Team
from app.models.user import User
from app.repositories import audit_repository, team_repository, user_repository
from app.schemas.team import InviteIn, TeamUpdateIn

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    slug = _NON_SLUG.sub("-", name.strip().lower()).strip("-")
    return slug[:50] or "team"


async def generate_unique_slug(db: AsyncSession, name: str) -> str:
    base = slugify(name)
    slug = base
    while await team_repository.get_by_slug(db, slug):
        slug = f"{base}-{secrets.token_hex(2)}"
    return slug


async def get_team_with_member_count(db: AsyncSession, user: User) -> tuple[Team, int]:
    team = await team_repository.get_by_id(db, user.team_id)
    if team is None:
        raise AppError(404, "NOT_FOUND", "Team not found")
    count = await team_repository.count_members(db, team.id)
    return team, count


async def update_team(
    db: AsyncSession, user: User, data: TeamUpdateIn, ip: str | None
) -> Team:
    team = await team_repository.get_by_id(db, user.team_id)
    if data.slug and data.slug != team.slug:
        if await team_repository.get_by_slug(db, data.slug):
            raise AppError(409, "SLUG_TAKEN", "This status page slug is already in use")
        team.slug = data.slug
    if data.name:
        team.name = data.name
    await audit_repository.log(
        db,
        action="team.updated",
        team_id=team.id,
        user_id=user.id,
        target_type="team",
        target_id=str(team.id),
        detail={"name": data.name, "slug": data.slug},
        ip=ip,
    )
    await db.commit()
    await db.refresh(team)
    return team


async def list_members(db: AsyncSession, user: User) -> list[User]:
    return await team_repository.list_members(db, user.team_id)


async def invite_member(
    db: AsyncSession, owner: User, data: InviteIn, ip: str | None
) -> tuple[User, str]:
    if await user_repository.get_by_email(db, data.email):
        raise AppError(409, "EMAIL_TAKEN", "An account with this email already exists")
    # v1 invite = direct add. The temp password is shown once; only its hash is stored.
    temp_password = secrets.token_urlsafe(9)
    user = await user_repository.create(
        db,
        team_id=owner.team_id,
        name=data.email.split("@")[0],
        email=data.email,
        password_hash=hash_password(temp_password),
        role=UserRole(data.role),
    )
    await audit_repository.log(
        db,
        action="team.member_invited",
        team_id=owner.team_id,
        user_id=owner.id,
        target_type="user",
        target_id=str(user.id),
        detail={"email": data.email, "role": data.role},
        ip=ip,
    )
    await db.commit()
    return user, temp_password
