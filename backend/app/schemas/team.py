import re
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.auth import TeamOut, UserOut

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_slug(value: str) -> str:
    value = value.strip().lower()
    if not SLUG_PATTERN.fullmatch(value):
        raise ValueError("slug may only contain lowercase letters, digits and single hyphens")
    return value


def _lowercase(value: str) -> str:
    return value.strip().lower()


class TeamDetailOut(TeamOut):
    members_count: int


class TeamUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    slug: str | None = Field(default=None, max_length=60)

    _norm_slug = field_validator("slug")(_validate_slug)


class InviteIn(BaseModel):
    email: EmailStr
    role: Literal["member", "viewer"]  # owners are created only at registration

    _norm_email = field_validator("email", mode="before")(_lowercase)


class InviteOut(BaseModel):
    user: UserOut
    temp_password: str  # shown exactly once — we store only the hash
