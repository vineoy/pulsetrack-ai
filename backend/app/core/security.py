import time
import uuid as uuidlib

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.user import User
from app.schemas.auth import TokenPayload

settings = get_settings()

ACCESS = "access"
REFRESH = "refresh"


def hash_password(password: str) -> str:
    # cost 12: ~250ms per hash, the right trade-off for a web app.
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _create_token(user: User, token_type: str, lifetime_seconds: int) -> tuple[str, TokenPayload]:
    now = int(time.time())
    payload = TokenPayload(
        sub=str(user.id),
        jti=uuidlib.uuid4().hex,
        type=token_type,
        team_id=str(user.team_id),
        role=user.role.value,
        iat=now,
        exp=now + lifetime_seconds,
    )
    token = jwt.encode(payload.model_dump(), settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, payload


def create_access_token(user: User) -> tuple[str, TokenPayload]:
    lifetime = settings.access_token_expire_minutes * 60
    return _create_token(user, ACCESS, lifetime)


def create_refresh_token(user: User) -> tuple[str, TokenPayload]:
    lifetime = settings.refresh_token_expire_days * 24 * 60 * 60
    return _create_token(user, REFRESH, lifetime)


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError:
        raise AppError(401, "TOKEN_EXPIRED", "Token has expired") from None
    except jwt.InvalidTokenError:
        raise AppError(401, "TOKEN_INVALID", "Token could not be verified") from None
    try:
        return TokenPayload(**payload)
    except Exception:
        raise AppError(401, "TOKEN_INVALID", "Token payload is malformed") from None
