"""Phase 3 tests: probe decision logic, check_job with mocked HTTP + test-DB/Redis
wiring, flap logic (2x DOWN -> OPEN once, 2x UP -> RESOLVED with downtime), scheduler query."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.security import hash_password
from app.models.check import Check
from app.models.incident import Incident, IncidentStatus
from app.models.monitor import Monitor
from app.models.team import Team
from app.models.user import User
from app.services.incident_service import apply_flap_logic, get_open_incident
from app.workers import checker
from app.workers.checker import check_job, decide_outcome


@pytest.fixture(autouse=True)
def _reset_mock_client():
    yield
    checker.set_client_for_testing(None)


async def make_team_monitor(db_session, slug, **monitor_kwargs) -> Monitor:
    team = Team(name=slug, slug=slug)
    db_session.add(team)
    await db_session.flush()
    db_session.add(
        User(
            team_id=team.id,
            name="Own",
            email=f"{slug}@x.dev",
            password_hash=hash_password("Secret123!"),
        )
    )
    monitor = Monitor(
        team_id=team.id,
        name="Test Target",
        url="https://target.dev/",
        interval_min=1,
        **monitor_kwargs,
    )
    db_session.add(monitor)
    await db_session.commit()
    await db_session.refresh(monitor)
    return monitor


async def add_check(db_session, monitor_id, status, minutes_ago):
    db_session.add(
        Check(
            monitor_id=monitor_id,
            status=status,
            latency_ms=100 if status == "UP" else None,
            status_code=200 if status == "UP" else 500,
            checked_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        )
    )
    await db_session.commit()


def wire_checker_to_test(db_session, redis_client):
    """check_job must write to the TEST database + TEST redis, like the API does
    via dependency_overrides. The worker uses module-level objects, so patch them."""
    checker.set_client_for_testing(
        httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, text="ok"))
        )
    )
    checker.async_session_factory = async_sessionmaker(
        db_session.bind, expire_on_commit=False
    )
    checker.redis_client = redis_client


class TestDecideOutcome:
    def test_2xx_and_3xx_are_up(self):
        assert decide_outcome(200, "hello", None) is True
        assert decide_outcome(302, "", None) is True

    def test_4xx_and_5xx_are_down(self):
        assert decide_outcome(404, "", None) is False
        assert decide_outcome(500, "", None) is False

    def test_missing_keyword_is_down(self):
        assert decide_outcome(200, "welcome to the site", "Checkout") is False

    def test_present_keyword_is_up(self):
        assert decide_outcome(200, "Checkout page", "Checkout") is True


class TestCheckJob:
    async def test_successful_probe_saves_up_check(self, db_session, redis_client, monkeypatch):
        monitor = await make_team_monitor(db_session, "worker-a")
        wire_checker_to_test(db_session, redis_client)

        result = await check_job({}, str(monitor.id))
        assert result.startswith("UP")

        checks = (await db_session.execute(select(Check))).scalars().all()
        assert len(checks) == 1
        assert checks[0].status == "UP"
        assert checks[0].latency_ms is not None

    async def test_probe_reschedules_next_check(self, db_session, redis_client):
        monitor = await make_team_monitor(db_session, "worker-b")
        wire_checker_to_test(db_session, redis_client)

        before = datetime.now(UTC)
        await check_job({}, str(monitor.id))

        async with async_sessionmaker(db_session.bind)() as fresh:
            refreshed = await fresh.get(Monitor, monitor.id)
            assert refreshed.next_check_at is not None
            assert refreshed.next_check_at > before

    async def test_dead_url_saves_down_check(self, db_session, redis_client):
        monitor = await make_team_monitor(db_session, "worker-c")
        checker.set_client_for_testing(
            httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda request: (_ for _ in ()).throw(
                        httpx.ConnectError("connection refused", request=request)
                    )
                )
            )
        )
        checker.async_session_factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
        checker.redis_client = redis_client

        result = await check_job({}, str(monitor.id))
        assert result.startswith("DOWN")

        check = (await db_session.execute(select(Check))).scalar_one()
        assert check.status == "DOWN"
        assert check.error and "http error" in check.error

    async def test_keyword_missing_is_down(self, db_session, redis_client):
        monitor = await make_team_monitor(db_session, "worker-d", keyword="Checkout")
        checker.set_client_for_testing(
            httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(200, text="no keyword here")
                )
            )
        )
        checker.async_session_factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
        checker.redis_client = redis_client

        result = await check_job({}, str(monitor.id))
        assert result.startswith("DOWN")
        check = (await db_session.execute(select(Check))).scalar_one()
        assert "keyword" in check.error

    async def test_job_never_crashes_on_garbage_monitor_id(self, db_session, redis_client):
        wire_checker_to_test(db_session, redis_client)
        with pytest.raises(ValueError):
            await check_job({}, "not-a-uuid")


class TestFlapLogic:
    async def test_two_downs_open_exactly_one_incident(self, db_session):
        monitor = await make_team_monitor(db_session, "flap-a")
        await add_check(db_session, monitor.id, "DOWN", 2)
        await add_check(db_session, monitor.id, "DOWN", 1)

        first = await apply_flap_logic(db_session, monitor)
        assert first is not None and first.status == IncidentStatus.OPEN

        # idempotent: re-running must NOT create a second incident
        second = await apply_flap_logic(db_session, monitor)
        assert second is None

        total = (await db_session.execute(select(func.count()).select_from(Incident))).scalar_one()
        assert total == 1

    async def test_two_ups_resolve_and_compute_downtime(self, db_session):
        monitor = await make_team_monitor(db_session, "flap-b")
        await add_check(db_session, monitor.id, "DOWN", 3)
        await add_check(db_session, monitor.id, "DOWN", 2)
        opened = await apply_flap_logic(db_session, monitor)
        assert opened.status == IncidentStatus.OPEN

        await add_check(db_session, monitor.id, "UP", 1)
        await add_check(db_session, monitor.id, "UP", 0)
        resolved = await apply_flap_logic(db_session, monitor)
        assert resolved is not None
        assert resolved.status == IncidentStatus.RESOLVED
        assert resolved.resolved_at is not None
        # started ~2-3 min ago; downtime positive and sane
        assert 0 < resolved.downtime_sec <= 600

    async def test_single_down_opens_nothing(self, db_session):
        monitor = await make_team_monitor(db_session, "flap-c")
        await add_check(db_session, monitor.id, "DOWN", 1)
        assert await apply_flap_logic(db_session, monitor) is None
        assert await get_open_incident(db_session, monitor.id) is None

    async def test_flapping_pattern_needs_two_consecutive_downs(self, db_session):
        monitor = await make_team_monitor(db_session, "flap-d")
        await add_check(db_session, monitor.id, "DOWN", 3)
        await add_check(db_session, monitor.id, "UP", 2)
        assert await apply_flap_logic(db_session, monitor) is None
        await add_check(db_session, monitor.id, "DOWN", 1)
        assert await apply_flap_logic(db_session, monitor) is None  # DOWN,UP,DOWN - no pair
        await add_check(db_session, monitor.id, "DOWN", 0)
        assert (await apply_flap_logic(db_session, monitor)) is not None


class TestSchedulerQuery:
    async def test_due_found_paused_skipped(self, db_session):
        due = await make_team_monitor(db_session, "sched-a")
        paused = await make_team_monitor(db_session, "sched-b", is_paused=True)

        now = datetime.now(UTC)
        async with async_sessionmaker(db_session.bind)() as fresh:
            m = await fresh.get(Monitor, due.id)
            m.next_check_at = now - timedelta(minutes=1)
            p = await fresh.get(Monitor, paused.id)
            p.next_check_at = now - timedelta(minutes=1)
            await fresh.commit()

            result = await fresh.execute(
                select(Monitor.id).where(
                    Monitor.is_paused.is_(False), Monitor.next_check_at <= now
                )
            )
            found = set(result.scalars().all())

        assert due.id in found
        assert paused.id not in found

    async def test_null_next_check_at_is_never_enqueued(self, db_session):
        # documents scheduler semantics: unscheduled == NULL, not "due now"
        unscheduled = await make_team_monitor(db_session, "sched-c")  # next_check_at=None

        now = datetime.now(UTC)
        result = await db_session.execute(
            select(Monitor.id).where(
                Monitor.is_paused.is_(False), Monitor.next_check_at <= now
            )
        )
        found = set(result.scalars().all())
        assert unscheduled.id not in found


class TestLock:
    async def test_lock_prevents_second_check(self, db_session, redis_client):
        monitor = await make_team_monitor(db_session, "lock-a")
        wire_checker_to_test(db_session, redis_client)

        # simulate another worker holding the lock
        lock_key = f"lock:monitor:{monitor.id}"
        await redis_client.set(lock_key, "1", nx=True, ex=60)

        result = await check_job({}, str(monitor.id))
        assert result == "skipped:locked"
        count = (
            await db_session.execute(select(func.count()).select_from(Check))
        ).scalar_one()
        assert count == 0
