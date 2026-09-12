import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(func.lower(User.email) == email.strip().lower()))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def create(db: AsyncSession, **fields: object) -> User:
    user = User(**fields)  # type: ignore[arg-type]
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
