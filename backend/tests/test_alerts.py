"""Phase 8 gap-fill: alert orchestration + ARQ alerter jobs (mocked Telegram)."""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.check import Check
from app.models.incident import Incident
from app.models.monitor import Monitor
from app.services import alert_service
from app.services import telegram_service as tg
from tests.test_auth import API, bearer, register_user

OK = {"ok": True, "result": {"message_id": 3}}


def _factory(db_session):
    return async_sessionmaker(db_session.bind, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _mock_telegram():
    tg.set_client_for_testing(
        httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json=OK))
        )
    )
    yield
    tg.set_client_for_testing(None)


async def open_incident(client, db_session, headers, name="Site"):
    mon = await client.post(
        f"{API}/monitors",
        json={"name": name, "url": "https://example.com", "interval_min": 1},
        headers=headers,
    )
    mid = uuid.UUID(mon.json()["data"]["id"])
    for _ in range(2):
        db_session.add(
            Check(
                monitor_id=mid,
                status="DOWN",
                status_code=500,
                error="server error 500",
                checked_at=datetime.now(UTC),
            )
        )
    await db_session.commit()
    from app.services.incident_service import apply_flap_logic

    monitor = await db_session.get(Monitor, mid)
    incident = await apply_flap_logic(db_session, monitor)
    await db_session.commit()
    return incident, monitor


class FakeRedis:
    def __init__(self):
        self.jobs: list = []

    async def enqueue_job(self, name, *args, **kwargs):
        self.jobs.append((name, args, kwargs))
        return None


class TestAlertService:
    async def test_open_recovery_escalation_texts(self, client, db_session):
        owner = await register_user(client, email="al@x.dev", team_name="Alert Co")
        headers = bearer(owner)
        await client.post(
            f"{API}/notification-channels", json={"telegram_chat_id": "111"}, headers=headers
        )
        incident, monitor = await open_incident(client, db_session, headers)
        assert any(r["status"] == "sent" for r in await alert_service.send_for_incident(
            db_session, incident, monitor, "open"))
        assert any(r["status"] == "sent" for r in await alert_service.send_for_incident(
            db_session, incident, monitor, "recovery"))
        assert any(r["status"] == "sent" for r in await alert_service.send_for_incident(
            db_session, incident, monitor, "escalation"))

    async def test_no_channel_and_maintenance_skip(self, client, db_session):
        owner = await register_user(client, email="al2@x.dev", team_name="Alert Two")
        headers = bearer(owner)
        incident, monitor = await open_incident(client, db_session, headers)
        skipped = await alert_service.send_for_incident(db_session, incident, monitor, "open")
        assert skipped == [{"status": "skipped", "reason": "no_channel"}]

        await client.post(
            f"{API}/notification-channels", json={"telegram_chat_id": "222"}, headers=headers
        )
        now = datetime.now(UTC)
        await client.post(
            f"{API}/maintenance",
            json={
                "monitor_id": None,
                "starts_at": (now - timedelta(minutes=1)).isoformat(),
                "ends_at": (now + timedelta(minutes=30)).isoformat(),
            },
            headers=headers,
        )
        muted = await alert_service.send_for_incident(db_session, incident, monitor, "open")
        assert muted == [{"status": "skipped", "reason": "maintenance"}]

    async def test_should_escalate_and_test_sender(self, client, db_session):
        assert alert_service.should_escalate(
            Incident(status="OPEN", monitor_id=uuid.uuid4(), team_id=uuid.uuid4())
        ) is True
        owner = await register_user(client, email="al3@x.dev", team_name="Alert Three")
        headers = bearer(owner)
        created = await client.post(
            f"{API}/notification-channels", json={"telegram_chat_id": "333"}, headers=headers
        )
        from app.repositories import notification_channel_repository

        channel = await notification_channel_repository.get_by_id(
            db_session, uuid.UUID(created.json()["data"]["id"])
        )
        ok, _ = await alert_service.send_test_for_channel(db_session, channel, None)
        assert ok is True


class TestAlerterJobs:
    async def test_open_sends_and_schedules_escalation(self, client, db_session, monkeypatch):
        import app.workers.alerter as alerter

        monkeypatch.setattr(
            alerter, "async_session_factory", _factory(db_session)
        )
        owner = await register_user(client, email="aj@x.dev", team_name="Alert Job")
        headers = bearer(owner)
        await client.post(
            f"{API}/notification-channels", json={"telegram_chat_id": "444"}, headers=headers
        )
        incident, _ = await open_incident(client, db_session, headers)
        ctx = {"redis": FakeRedis()}
        result = await alerter.telegram_alert_job(ctx, str(incident.id), "open")
        assert "escalation scheduled" in result
        escalations = [j for j in ctx["redis"].jobs if j[0] == "telegram_alert_job"]
        assert any(j[1][1] == "escalation" for j in escalations)

    async def test_escalation_marks_and_dedupes(self, client, db_session, monkeypatch):
        import app.workers.alerter as alerter

        monkeypatch.setattr(
            alerter, "async_session_factory", _factory(db_session)
        )
        owner = await register_user(client, email="aj2@x.dev", team_name="Alert Job Two")
        headers = bearer(owner)
        await client.post(
            f"{API}/notification-channels", json={"telegram_chat_id": "555"}, headers=headers
        )
        incident, _ = await open_incident(client, db_session, headers)
        fake_ctx: dict = {"redis": FakeRedis()}
        escalation = await alerter.telegram_alert_job(fake_ctx, str(incident.id), "escalation")
        assert escalation == "escalated"
        # Second escalation for the same incident is skipped (one escalation only).
        repeat = await alerter.telegram_alert_job(fake_ctx, str(incident.id), "escalation")
        assert "skipped" in repeat
        missing_channel = await alerter.telegram_test_job(
            fake_ctx, "00000000-0000-0000-0000-000000000000"
        )
        assert missing_channel == "skipped:channel_gone"
        gone = await alerter.telegram_alert_job(fake_ctx, str(uuid.uuid4()), "open")
        assert "gone" in gone

    async def test_sweep_catches_stale_open(self, client, db_session, monkeypatch):
        import app.workers.alerter as alerter

        monkeypatch.setattr(
            alerter, "async_session_factory", _factory(db_session)
        )
        owner = await register_user(client, email="sw@x.dev", team_name="Sweep Co")
        headers = bearer(owner)
        await client.post(
            f"{API}/notification-channels", json={"telegram_chat_id": "666"}, headers=headers
        )
        incident, _ = await open_incident(client, db_session, headers)
        async with async_sessionmaker(db_session.bind, expire_on_commit=False)() as fresh:
            stale = await fresh.get(Incident, incident.id)
            stale.started_at = datetime.now(UTC) - timedelta(minutes=30)
            await fresh.commit()
        ctx = {"redis": FakeRedis()}
        assert await alerter.sweep_stale_escalations(ctx) == 1
        assert any(j[1][1] == "escalation" for j in ctx["redis"].jobs)
        # Sweep only enqueues (sending happens in telegram_alert_job). A second
        # sweep re-enqueues while the incident is still un-escalated — dedupe
        # happens at send time via should_escalate (covered above).
        assert await alerter.sweep_stale_escalations({"redis": FakeRedis()}) == 1
