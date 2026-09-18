"""Phase 8 gap-fill: heartbeat CRUD + ping + checker (mocked Telegram)."""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.alert_log import AlertLog
from app.models.heartbeat import Heartbeat
from app.services import telegram_service as tg
from tests.test_auth import API, bearer, register_user


@pytest.fixture(autouse=True)
def _isolate_router_redis(redis_client, monkeypatch):
    # The router uses the process-global redis client (bound to one event loop).
    # Point it at test redis: one test's loop must never poison another's
    # (pytest-asyncio runs each test in a FRESH loop).
    import app.api.v1.routers.heartbeats as hb_router

    monkeypatch.setattr(hb_router, "redis_client", redis_client)
    yield


@pytest.fixture(autouse=True)
def _mock_telegram():
    tg.set_client_for_testing(
        httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
            )
        )
    )
    yield
    tg.set_client_for_testing(None)


def _factory(db_session):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    return async_sessionmaker(db_session.bind, expire_on_commit=False)


async def make_heartbeat(client, headers, name="cron", period=5, grace=2):
    resp = await client.post(
        f"{API}/heartbeats",
        json={"name": name, "period_min": period, "grace_min": grace},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


class TestHeartbeatRouter:
    async def test_crud_and_validation(self, client):
        owner = await register_user(client, email="hb@x.dev", team_name="Hb Co")
        headers = bearer(owner)
        created = await make_heartbeat(client, headers)
        assert created["ping_key"].startswith("hb_") and created["status"] == "ALIVE"
        bad = await client.post(
            f"{API}/heartbeats",
            json={"name": "x", "period_min": 0, "grace_min": 2},
            headers=headers,
        )
        assert bad.status_code == 422
        listed = await client.get(f"{API}/heartbeats", headers=headers)
        assert len(listed.json()["data"]) == 1
        evil = await register_user(client, email="hb-evil@x.dev", team_name="Hb Evil")
        assert (
            await client.delete(
                f"{API}/heartbeats/{created['id']}", headers=bearer(evil)
            )
        ).status_code == 404
        assert (
            await client.delete(f"{API}/heartbeats/{created['id']}", headers=headers)
        ).status_code == 200
        gone = await client.post(f"{API}/heartbeats/{created['ping_key']}/ping")
        assert gone.status_code == 404

    async def test_ping_and_recovery(self, client, db_session):
        owner = await register_user(client, email="hb2@x.dev", team_name="Hb Two")
        headers = bearer(owner)
        await client.post(
            f"{API}/notification-channels", json={"telegram_chat_id": "777"}, headers=headers
        )
        created = await make_heartbeat(client, headers)
        pinged = await client.post(f"{API}/heartbeats/{created['ping_key']}/ping")
        assert pinged.json()["data"] == {"ok": True, "status": "ALIVE"}
        assert (await client.post(f"{API}/heartbeats/bad-key/ping")).status_code == 404

        # Force MISSING, then ping → ALIVE + recovery alert logged.
        async with async_sessionmaker(db_session.bind, expire_on_commit=False)() as fresh:
            hb = await fresh.get(Heartbeat, uuid.UUID(created["id"]))
            hb.status = "MISSING"
            await fresh.commit()
        recovered = await client.post(f"{API}/heartbeats/{created['ping_key']}/ping")
        assert recovered.json()["data"]["status"] == "ALIVE"
        kinds = [
            r.kind
            for r in (await db_session.execute(select(AlertLog))).scalars().all()
        ]
        assert "recovery" in kinds


class TestHeartbeatChecker:
    async def test_silent_goes_missing_with_alert(self, client, db_session, monkeypatch):
        import app.workers.heartbeat_checker as checker

        monkeypatch.setattr(
            checker, "async_session_factory", _factory(db_session)
        )
        owner = await register_user(client, email="hb3@x.dev", team_name="Hb Three")
        headers = bearer(owner)
        await client.post(
            f"{API}/notification-channels", json={"telegram_chat_id": "888"}, headers=headers
        )
        created = await make_heartbeat(client, headers, period=5, grace=2)
        async with async_sessionmaker(db_session.bind, expire_on_commit=False)() as fresh:
            hb = await fresh.get(Heartbeat, uuid.UUID(created["id"]))
            hb.last_ping_at = datetime.now(UTC) - timedelta(minutes=30)
            await fresh.commit()
        assert await checker.heartbeat_checker({}) == "ok checked=1 missing=1"
        async with async_sessionmaker(db_session.bind, expire_on_commit=False)() as fresh:
            assert (await fresh.get(Heartbeat, uuid.UUID(created["id"]))).status == "MISSING"
        # Second run: already MISSING, nothing more to do.
        assert await checker.heartbeat_checker({}) == "ok checked=0 missing=0"

    async def test_fresh_and_no_channel_paths(self, client, db_session, monkeypatch):
        import app.workers.heartbeat_checker as checker

        monkeypatch.setattr(
            checker, "async_session_factory", _factory(db_session)
        )
        owner = await register_user(client, email="hb4@x.dev", team_name="Hb Four")
        headers = bearer(owner)
        created = await make_heartbeat(client, headers)
        await client.post(f"{API}/heartbeats/{created['ping_key']}/ping")
        assert await checker.heartbeat_checker({}) == "ok checked=0 missing=0"

        # No Telegram channel → skipped receipt, still marked MISSING.
        async with async_sessionmaker(db_session.bind, expire_on_commit=False)() as fresh:
            hb = await fresh.get(Heartbeat, uuid.UUID(created["id"]))
            hb.last_ping_at = datetime.now(UTC) - timedelta(minutes=30)
            await fresh.commit()
        assert await checker.heartbeat_checker({}) == "ok checked=1 missing=1"
        errors = [
            r.error
            for r in (await db_session.execute(select(AlertLog))).scalars().all()
        ]
        assert "no active telegram channel" in errors
