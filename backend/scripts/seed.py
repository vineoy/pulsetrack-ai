"""Seed a demo team + owner so the app is usable immediately.

Run: uv run python scripts/seed.py   (requires `alembic upgrade head` first)
"""

import asyncio

from sqlalchemy import select

from app.core.db import async_session_factory
from app.core.security import hash_password
from app.models.enums import TeamPlan, UserRole
from app.models.team import Team
from app.models.user import User

DEMO_EMAIL = "demo@pulsetrack.dev"
DEMO_PASSWORD = "Demo1234!"


async def main() -> None:
    async with async_session_factory() as db:
        existing = await db.execute(select(User).where(User.email == DEMO_EMAIL))
        if existing.scalar_one_or_none() is not None:
            print(f"Seed skipped: {DEMO_EMAIL} already exists.")
            return

        team = Team(name="Demo Team", slug="demo-team", plan=TeamPlan.FREE)
        db.add(team)
        await db.flush()
        owner = User(
            team_id=team.id,
            name="Demo Owner",
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            role=UserRole.OWNER,
        )
        db.add(owner)
        await db.commit()
        print(f"Seeded team 'demo-team' (free plan) with owner {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
