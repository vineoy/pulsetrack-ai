import time
import uuid as uuidlib

from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.security import (
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User
from app.repositories import audit_repository, team_repository, user_repository
from app.schemas.auth import RegisterIn, TokenPairOut, TokenPayload
from app.services.team_service import generate_unique_slug

# Refresh-token rotation state. Key exists => token is alive; missing => used/revoked.
REFRESH_KEY = "refresh:{user_id}:{jti}"
# Logout blacklist for access tokens, TTL = remaining token lifetime.
BLACKLIST_KEY = "jwt:black:{jti}"


async def _issue_token_pair(redis: aioredis.Redis, user: User) -> TokenPairOut:
    access, access_payload = create_access_token(user)
    refresh, refresh_payload = create_refresh_token(user)
    await redis.set(
        REFRESH_KEY.format(user_id=user.id, jti=refresh_payload.jti),
        "1",
        ex=refresh_payload.exp - refresh_payload.iat,
    )
    return TokenPairOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=access_payload.exp - access_payload.iat,
    )


async def register(
    db: AsyncSession, redis: aioredis.Redis, data: RegisterIn, ip: str | None
) -> tuple[User, TokenPairOut]:
    if await user_repository.get_by_email(db, data.email):
        raise AppError(409, "EMAIL_TAKEN", "An account with this email already exists")

    slug = await generate_unique_slug(db, data.team_name)
    team = await team_repository.create(db, name=data.team_name, slug=slug)
    user = await user_repository.create(
        db,
        team_id=team.id,
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.OWNER,
    )
    await audit_repository.log(
        db,
        action="auth.register",
        team_id=team.id,
        user_id=user.id,
        target_type="user",
        target_id=str(user.id),
        detail={"email": user.email, "team_slug": team.slug},
        ip=ip,
    )
    await db.commit()
    tokens = await _issue_token_pair(redis, user)
    return user, tokens


async def login(
    db: AsyncSession, redis: aioredis.Redis, email: str, password: str, ip: str | None
) -> tuple[User, TokenPairOut]:
    user = await user_repository.get_by_email(db, email)
    # Same error for unknown email and wrong password: never reveal which one failed.
    if user is None or not verify_password(password, user.password_hash):
        await audit_repository.log(
            db,
            action="auth.login_failed",
            team_id=user.team_id if user else None,
            user_id=user.id if user else None,
            detail={"email": email.strip().lower()},
            ip=ip,
        )
        await db.commit()
        raise AppError(401, "INVALID_CREDENTIALS", "Email or password is incorrect")
    if not user.is_active:
        raise AppError(403, "ACCOUNT_DISABLED", "This account has been disabled")

    await audit_repository.log(
        db,
        action="auth.login",
        team_id=user.team_id,
        user_id=user.id,
        target_type="user",
        target_id=str(user.id),
        ip=ip,
    )
    await db.commit()
    tokens = await _issue_token_pair(redis, user)
    return user, tokens


async def refresh(
    db: AsyncSession, redis: aioredis.Redis, refresh_token: str, ip: str | None
) -> TokenPairOut:
    payload = decode_token(refresh_token)
    if payload.type != REFRESH:
        raise AppError(401, "TOKEN_INVALID", "Not a refresh token")

    key = REFRESH_KEY.format(user_id=payload.sub, jti=payload.jti)
    if not await redis.exists(key):
        # A valid-but-unknown token means it was already used or revoked: theft signal.
        # Revoke the whole family so the attacker (and the user) must log in again.
        async for stale in redis.scan_iter(match=f"refresh:{payload.sub}:*"):
            await redis.delete(stale)
        user_for_audit = await user_repository.get_by_id(db, uuidlib.UUID(payload.sub))
        await audit_repository.log(
            db,
            action="auth.refresh_reuse_detected",
            team_id=user_for_audit.team_id if user_for_audit else None,
            user_id=user_for_audit.id if user_for_audit else None,
            detail={"jti": payload.jti},
            ip=ip,
        )
        await db.commit()
        raise AppError(
            401,
            "REFRESH_REUSE_DETECTED",
            "Refresh token was already used. All sessions were revoked — please log in again.",
        )

    await redis.delete(key)
    user = await user_repository.get_by_id(db, uuidlib.UUID(payload.sub))
    if user is None or not user.is_active:
        raise AppError(401, "TOKEN_INVALID", "User no longer exists or is disabled")

    await audit_repository.log(
        db,
        action="auth.refresh",
        team_id=user.team_id,
        user_id=user.id,
        detail={"jti": payload.jti},
        ip=ip,
    )
    await db.commit()
    return await _issue_token_pair(redis, user)


async def logout(
    db: AsyncSession,
    redis: aioredis.Redis,
    user: User,
    access_payload: TokenPayload,
    refresh_token: str | None,
    ip: str | None,
) -> None:
    ttl = access_payload.exp - int(time.time())
    if ttl > 0:
        await redis.set(BLACKLIST_KEY.format(jti=access_payload.jti), "1", ex=ttl)
    if refresh_token:
        try:
            refresh_payload = decode_token(refresh_token)
        except AppError:
            refresh_payload = None
        if refresh_payload and refresh_payload.type == REFRESH:
            await redis.delete(
                REFRESH_KEY.format(user_id=refresh_payload.sub, jti=refresh_payload.jti)
            )
    await audit_repository.log(
        db,
        action="auth.logout",
        team_id=user.team_id,
        user_id=user.id,
        detail={"jti": access_payload.jti},
        ip=ip,
    )
    await db.commit()
