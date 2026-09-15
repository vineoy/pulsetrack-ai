"""Seed a demo team + owner + monitors with fake check history so the dashboard
has data before the real worker exists (Phase 3).

Run: uv run python scripts/seed.py   (requires `alembic upgrade head` first)
"""

import asyncio
import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.db import async_session_factory
from app.core.security import hash_password
from app.models.check import Check
from app.models.enums import TeamPlan, UserRole
from app.models.monitor import Monitor
from app.models.team import Team
from app.models.user import User

DEMO_EMAIL = "demo@pulsetrack.dev"
DEMO_PASSWORD = "Demo1234!"

DEMO_MONITORS = [
    {"name": "Marketing Site", "url": "https://example.com", "interval_min": 5, "keyword": None},
    {
        "name": "Checkout API",
        "url": "https://httpbin.org/status/200",
        "interval_min": 1,
        "keyword": None,
    },
    {"name": "Docs Portal", "url": "https://example.org", "interval_min": 10, "keyword": "Example"},
]


def _fake_checks(monitor_id: uuid.UUID) -> list[Check]:
    """~3 hours of 1-minute checks: mostly UP at 120-260ms with a short outage window."""
    now = datetime.now(UTC)
    checks = []
    for minutes_ago in range(180, -1, -1):
        at = now - timedelta(minutes=minutes_ago)
        in_outage = 95 <= minutes_ago <= 104  # a 10-minute outage to look at
        if in_outage:
            checks.append(
                Check(
                    monitor_id=monitor_id,
                    status="DOWN",
                    latency_ms=None,
                    status_code=None,
                    error="connection timeout after 10s",
                    checked_at=at,
                )
            )
        else:
            checks.append(
                Check(
                    monitor_id=monitor_id,
                    status="UP",
                    latency_ms=random.randint(120, 260),
                    status_code=200,
                    error=None,
                    checked_at=at,
                )
            )
    return checks


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
        for spec in DEMO_MONITORS:
            monitor = Monitor(team_id=team.id, **spec)
            db.add(monitor)
            await db.flush()
            for check in _fake_checks(monitor.id):
                db.add(check)
        await db.commit()
        print(f"Seeded team 'demo-team' (free plan) with owner {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print(f"  + {len(DEMO_MONITORS)} monitors, each with ~180 fake checks (one outage window)")


if __name__ == "__main__":
    asyncio.run(main())
