import hashlib
import hmac
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey

KEY_PREFIX = "pk_live_"
PREFIX_LEN = 12  # "pk_live_" + 4 chars: enough to identify, useless to forge


def generate_raw_key() -> str:
    return f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def prefix_of(raw: str) -> str:
    return raw[:PREFIX_LEN]


def verify_key(raw: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_key(raw), stored_hash)


async def list_for_team(db: AsyncSession, team_id: uuid.UUID) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.team_id == team_id).order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def get_by_prefix(db: AsyncSession, prefix: str) -> ApiKey | None:
    result = await db.execute(select(ApiKey).where(ApiKey.prefix == prefix))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, key_id: uuid.UUID) -> ApiKey | None:
    return await db.get(ApiKey, key_id)


async def create(
    db: AsyncSession,
    *,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
) -> tuple[ApiKey, str]:
    """Create a key. Returns (row, raw_key_shown_once). Prefix pre-checked for
    uniqueness (unique constraint stays as the race backstop)."""
    for _ in range(5):
        raw = generate_raw_key()
        if await get_by_prefix(db, prefix_of(raw)) is not None:
            continue
        row = ApiKey(
            team_id=team_id,
            user_id=user_id,
            name=name,
            prefix=prefix_of(raw),
            key_hash=hash_key(raw),
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row, raw
    raise RuntimeError("could not mint a unique API key prefix")


async def delete(db: AsyncSession, row: ApiKey) -> None:
    await db.delete(row)
    await db.flush()
