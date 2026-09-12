import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

# bcrypt silently truncates input beyond 72 bytes, so reject longer passwords
# instead of letting users believe 100 characters were hashed.
PASSWORD_MAX_BYTES = 72


def _check_password_size(value: str) -> str:
    if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValueError(f"password must be at most {PASSWORD_MAX_BYTES} bytes")
    return value


def _lowercase(value: str) -> str:
    return value.strip().lower()


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    team_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    _norm_email = field_validator("email", mode="before")(_lowercase)
    _norm_password = field_validator("password")(_check_password_size)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    _norm_email = field_validator("email", mode="before")(_lowercase)


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: str | None = None


class TokenPayload(BaseModel):
    sub: str
    jti: str
    type: str
    team_id: str | None = None
    role: str | None = None
    iat: int
    exp: int


class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime


class TeamOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    slug: str
    plan: str
    created_at: datetime


class AuthOut(TokenPairOut):
    user: UserOut


class MeOut(BaseModel):
    user: UserOut
    team: TeamOut
