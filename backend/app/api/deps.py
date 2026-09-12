import uuid
from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.exceptions import AppError
from app.core.redis import get_redis
from app.core.security import decode_token
from app.models.user import User
from app.repositories import user_repository
from app.schemas.auth import TokenPayload

bearer = HTTPBearer(auto_error=False)

DBDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _auth_error(code: str, message: str) -> AppError:
    return AppError(401, code, message, headers={"WWW-Authenticate": "Bearer"})


async def get_token_payload(
    creds: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)],
) -> TokenPayload:
    if creds is None:
        raise _auth_error("NOT_AUTHENTICATED", "Missing bearer token")
    return decode_token(creds.credentials)


TokenPayloadDep = Annotated[TokenPayload, Depends(get_token_payload)]


async def get_current_user(payload: TokenPayloadDep, db: DBDep, redis: RedisDep) -> User:
    if payload.type != "access":
        raise _auth_error("TOKEN_INVALID", "Wrong token type")
    if await redis.exists(f"jwt:black:{payload.jti}"):
        raise _auth_error("TOKEN_REVOKED", "Token was revoked at logout")
    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError:
        raise _auth_error("TOKEN_INVALID", "Malformed token subject") from None
    user = await user_repository.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise _auth_error("TOKEN_INVALID", "User no longer exists or is disabled")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    async def checker(user: CurrentUser) -> User:
        if user.role.value not in roles:
            raise AppError(
                403, "FORBIDDEN", f"This action requires one of roles: {', '.join(roles)}"
            )
        return user

    return Annotated[User, Depends(checker)]


OwnerUser = require_role("owner")
MemberUser = require_role("owner", "member")
