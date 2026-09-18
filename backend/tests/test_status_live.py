"""Phase 8 gap-fill: public status API, live fan-out helpers, WS auth."""

import json
import uuid
from datetime import UTC, datetime

from app.models.check import Check
from app.models.monitor import Monitor
from app.services import live_service as live
from tests.test_auth import API, bearer, register_user


async def seed_team_with_monitor(client, email="st@x.dev", team="Status Co", name="Site"):
    owner = await register_user(client, email=email, team_name=team)
    headers = bearer(owner)
    mon = await client.post(
        f"{API}/monitors",
        json={"name": name, "url": "https://example.com", "interval_min": 1},
        headers=headers,
    )
    assert mon.status_code == 201, mon.text
    return owner, headers, mon.json()["data"]


async def add_checks(db_session, monitor_id, statuses):
    for _i, st in enumerate(statuses):
        db_session.add(
            Check(
                monitor_id=monitor_id,
                status=st,
                latency_ms=100 if st == "UP" else None,
                status_code=200 if st == "UP" else 500,
                error=None if st == "UP" else "server error 500",
                checked_at=datetime.now(UTC),
            )
        )
    await db_session.commit()


class TestPublicStatus:
    async def test_page_incidents_privacy_and_cache(self, client, db_session, redis_client):
        _, headers, monitor = await seed_team_with_monitor(client)
        await add_checks(db_session, uuid.UUID(monitor["id"]), ["UP"])

        from app.core.redis import get_redis  # noqa: F401  (documents cache layer)

        slug = (await client.get(f"{API}/teams/me", headers=headers)).json()["data"]["slug"]
        first = await client.get(f"/status/{slug}")
        assert first.status_code == 200
        body = first.json()["data"]
        assert body["overall"] == "operational" and body["open_incidents"] == 0
        assert body["monitors"][0]["name"] == "Site"
        dumped = json.dumps(body)
        assert "example.com" not in dumped and "@" not in dumped  # privacy: names only

        second = await client.get(f"/status/{slug}")
        assert second.json()["data"] == body  # cache hit, identical
        assert await redis_client.get(f"public:{slug}") is not None

        versioned = await client.get(f"{API}/status/{slug}")
        assert versioned.status_code == 200
        missing = await client.get("/status/no-such-team")
        assert missing.status_code == 404

    async def test_degraded_and_outage_levels(self, client, db_session):
        _, headers, m1 = await seed_team_with_monitor(client, email="lv@x.dev", team="Lv Co")
        mon2 = await client.post(
            f"{API}/monitors",
            json={"name": "Two", "url": "https://two.dev", "interval_min": 1},
            headers=headers,
        )
        await add_checks(db_session, uuid.UUID(m1["id"]), ["UP"])
        await add_checks(db_session, uuid.UUID(mon2.json()["data"]["id"]), ["DOWN", "DOWN"])
        slug = (await client.get(f"{API}/teams/me", headers=headers)).json()["data"]["slug"]
        body = (await client.get(f"/status/{slug}")).json()["data"]
        assert body["overall"] == "degraded"  # one UP, one DOWN

    async def test_incidents_list_and_limit(self, client, db_session):
        _, headers, monitor = await seed_team_with_monitor(client, email="li@x.dev", team="Li Co")
        await add_checks(db_session, uuid.UUID(monitor["id"]), ["DOWN", "DOWN"])
        from app.services.incident_service import apply_flap_logic

        m = await db_session.get(Monitor, uuid.UUID(monitor["id"]))
        await apply_flap_logic(db_session, m)
        await db_session.commit()
        slug = (await client.get(f"{API}/teams/me", headers=headers)).json()["data"]["slug"]
        items = (await client.get(f"/status/{slug}/incidents")).json()["data"]
        assert len(items) == 1 and items[0]["status"] == "OPEN"
        limited = await client.get(f"/status/{slug}/incidents", params={"limit": 1})
        assert len(limited.json()["data"]) == 1
        assert (await client.get("/status/nope/incidents")).status_code == 404


class TestLiveHelpers:
    def test_build_event_shape(self):
        event = live.build_check_event(
            team_id=uuid.uuid4(),
            monitor_id=uuid.uuid4(),
            status="DOWN",
            latency_ms=None,
            status_code=None,
            checked_at=datetime.now(UTC),
            incident="OPEN",
        )
        assert event["type"] == "check" and event["incident"] == "OPEN"

    async def test_publish_and_invalidate(self, redis_client):
        event = live.build_check_event(
            team_id="t",
            monitor_id="m",
            status="UP",
            latency_ms=5,
            status_code=200,
            checked_at=datetime.now(UTC),
        )
        await live.publish_check(redis_client, event)  # never raises
        await redis_client.set("public:s", "x")
        await redis_client.set("public:s:incidents", "y")
        await live.invalidate_public_cache(redis_client, "s")
        assert await redis_client.get("public:s") is None
        assert await redis_client.get("public:s:incidents") is None
        await live.invalidate_public_cache(redis_client, None)  # no-op, no raise
        assert live.public_incidents_key("s") == "public:s:incidents"


def _factory(db_session):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    return async_sessionmaker(db_session.bind, expire_on_commit=False)


class TestWsAuth:
    async def test_valid_missing_and_bad_tokens(
        self, client, db_session, redis_client, monkeypatch
    ):
        import app.api.ws as wsm

        owner = await register_user(client, email="ws@x.dev", team_name="Ws Co")
        monkeypatch.setattr(wsm, "async_session_factory", _factory(db_session))
        monkeypatch.setattr(wsm, "redis_client", redis_client)
        user, error = await wsm._auth_ws(owner["access_token"])
        assert user is not None and error is None and str(user.team_id)
        assert await wsm._auth_ws(None) == (None, "missing token")
        assert (await wsm._auth_ws("garbage"))[0] is None
        assert [r.path for r in wsm.router.routes] == ["/ws/monitors"]
