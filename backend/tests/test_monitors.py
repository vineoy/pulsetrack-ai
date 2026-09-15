"""Phase 2 tests: monitor CRUD, free-plan limit, RBAC, team isolation, checks page, stats."""

import uuid
from datetime import UTC, datetime, timedelta

from tests.test_auth import API, bearer, login, register_user


async def create_team_with_monitor(client, email: str = "mon@owner.dev", **monitor_fields) -> dict:
    """Register a team, create one monitor, return {auth, monitor, owner_auth}."""
    auth = await register_user(client, email=email, team_name=f"Team {email}")
    payload = {"name": "My Site", "url": "https://example.com", "interval_min": 5, **monitor_fields}
    resp = await client.post(f"{API}/monitors", json=payload, headers=bearer(auth))
    assert resp.status_code == 201, resp.text
    return {"auth": auth, "monitor": resp.json()["data"], "payload": payload}


async def seed_checks(db_session, monitor_id, rows: list[tuple[str, int | None, int]]) -> None:
    """rows = [(status, latency_ms, minutes_ago), ...]"""
    from app.models.check import Check

    now = datetime.now(UTC)
    for status_value, latency, minutes_ago in rows:
        db_session.add(
            Check(
                monitor_id=monitor_id,
                status=status_value,
                latency_ms=latency,
                status_code=200 if status_value == "UP" else None,
                checked_at=now - timedelta(minutes=minutes_ago),
            )
        )
    await db_session.commit()


class TestMonitorCrud:
    async def test_create_and_get_detail(self, client):
        env = await create_team_with_monitor(client)
        headers = bearer(env["auth"])

        resp = await client.get(f"{API}/monitors/{env['monitor']['id']}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["name"] == "My Site"
        assert body["url"] == "https://example.com/"
        assert body["last_20_checks"] == []
        assert body["uptime_pct_30d"] is None  # no checks yet

    async def test_invalid_url_rejected(self, client):
        auth = await register_user(client, email="badurl@x.dev", team_name="Bad URL Co")
        resp = await client.post(
            f"{API}/monitors",
            json={"name": "X", "url": "not-a-url", "interval_min": 5},
            headers=bearer(auth),
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    async def test_invalid_interval_rejected(self, client):
        auth = await register_user(client, email="badint@x.dev", team_name="Bad Int Co")
        resp = await client.post(
            f"{API}/monitors",
            json={"name": "X", "url": "https://example.com", "interval_min": 7},
            headers=bearer(auth),
        )
        assert resp.status_code == 422

    async def test_update_changes_fields(self, client):
        env = await create_team_with_monitor(client, email="upd@x.dev")
        resp = await client.put(
            f"{API}/monitors/{env['monitor']['id']}",
            json={"name": "Renamed", "interval_min": 30, "keyword": "hello"},
            headers=bearer(env["auth"]),
        )
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["name"] == "Renamed"
        assert body["interval_min"] == 30
        assert body["keyword"] == "hello"

    async def test_pause_resume(self, client):
        env = await create_team_with_monitor(client, email="pause@x.dev")
        mid = env["monitor"]["id"]

        resp = await client.post(f"{API}/monitors/{mid}/pause", headers=bearer(env["auth"]))
        assert resp.status_code == 200
        assert resp.json()["data"]["is_paused"] is True

        resp = await client.post(f"{API}/monitors/{mid}/resume", headers=bearer(env["auth"]))
        assert resp.status_code == 200
        assert resp.json()["data"]["is_paused"] is False

    async def test_owner_can_delete(self, client):
        env = await create_team_with_monitor(client, email="del@x.dev")
        mid = env["monitor"]["id"]

        resp = await client.delete(f"{API}/monitors/{mid}", headers=bearer(env["auth"]))
        assert resp.status_code == 200

        resp = await client.get(f"{API}/monitors/{mid}", headers=bearer(env["auth"]))
        assert resp.status_code == 404


class TestPlanLimit:
    async def test_11th_monitor_rejected_on_free_plan(self, client):
        auth = await register_user(client, email="limit@x.dev", team_name="Limit Co")
        for i in range(10):
            resp = await client.post(
                f"{API}/monitors",
                json={"name": f"Monitor {i}", "url": "https://example.com", "interval_min": 5},
                headers=bearer(auth),
            )
            assert resp.status_code == 201, f"#{i + 1} should be allowed"

        resp = await client.post(
            f"{API}/monitors",
            json={"name": "One Too Many", "url": "https://example.com", "interval_min": 5},
            headers=bearer(auth),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "PLAN_LIMIT_REACHED"


class TestRbacAndTenancy:
    async def test_viewer_cannot_create_monitor(self, client):
        owner = await register_user(client, email="rbac@x.dev", team_name="RBAC Co")
        resp = await client.post(
            f"{API}/teams/invite",
            json={"email": "view@x.dev", "role": "viewer"},
            headers=bearer(owner),
        )
        viewer = await login(client, "view@x.dev", resp.json()["data"]["temp_password"])

        resp = await client.post(
            f"{API}/monitors",
            json={"name": "Nope", "url": "https://example.com", "interval_min": 5},
            headers=bearer(viewer),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"

    async def test_other_team_monitor_is_404_not_403(self, client):
        env_a = await create_team_with_monitor(client, email="iso-a@x.dev")
        env_b_auth = await register_user(client, email="iso-b@x.dev", team_name="Isolation B")

        resp = await client.get(
            f"{API}/monitors/{env_a['monitor']['id']}", headers=bearer(env_b_auth)
        )
        assert resp.status_code == 404  # not 403: never leak other teams' resource existence

    async def test_list_only_shows_own_monitors(self, client):
        await create_team_with_monitor(client, email="list-a@x.dev")
        auth_b = await register_user(client, email="list-b@x.dev", team_name="List B")
        resp = await client.post(
            f"{API}/monitors",
            json={"name": "B Only", "url": "https://example.com", "interval_min": 5},
            headers=bearer(auth_b),
        )
        assert resp.status_code == 201

        resp = await client.get(f"{API}/monitors", headers=bearer(auth_b))
        names = [monitor["name"] for monitor in resp.json()["data"]]
        assert names == ["B Only"]


class TestChecksAndStats:
    async def test_checks_page_pagination(self, client, db_session):
        env = await create_team_with_monitor(client, email="checks@x.dev")
        mid = uuid.UUID(env["monitor"]["id"])
        rows = [("UP", 150, i) for i in range(75)]
        await seed_checks(db_session, mid, rows)

        resp = await client.get(
            f"{API}/monitors/{mid}/checks",
            params={"page": 1, "limit": 50},
            headers=bearer(env["auth"]),
        )
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["total"] == 75
        assert len(body["items"]) == 50
        # newest first ordering
        times = [item["checked_at"] for item in body["items"]]
        assert times == sorted(times, reverse=True)

    async def test_stats_computed_from_checks(self, client, db_session):
        env = await create_team_with_monitor(client, email="stats@x.dev")
        mid = uuid.UUID(env["monitor"]["id"])
        rows = [("UP", 100, 50), ("UP", 200, 40), ("UP", 300, 30), ("DOWN", None, 20)]
        await seed_checks(db_session, mid, rows)

        resp = await client.get(
            f"{API}/monitors/{mid}/stats", params={"days": 30}, headers=bearer(env["auth"])
        )
        assert resp.status_code == 200
        stats = resp.json()["data"]
        assert stats["total_checks"] == 4
        assert stats["up_checks"] == 3
        assert stats["down_checks"] == 1
        assert stats["uptime_pct"] == 75.0
        assert stats["avg_latency_ms"] == 200.0
        assert stats["p50_latency_ms"] == 200.0
        assert stats["p95_latency_ms"] == 290.0

    async def test_stats_empty_monitor(self, client):
        env = await create_team_with_monitor(client, email="emptystats@x.dev")
        resp = await client.get(
            f"{API}/monitors/{env['monitor']['id']}/stats", headers=bearer(env["auth"])
        )
        assert resp.status_code == 200
        stats = resp.json()["data"]
        assert stats["total_checks"] == 0
        assert stats["uptime_pct"] == 0.0

    async def test_dashboard_list_shows_current_status(self, client, db_session):
        env = await create_team_with_monitor(client, email="dash@x.dev")
        mid = uuid.UUID(env["monitor"]["id"])
        await seed_checks(db_session, mid, [("UP", 120, 2)])

        resp = await client.get(f"{API}/monitors", headers=bearer(env["auth"]))
        row = resp.json()["data"][0]
        assert row["current_status"] == "UP"
        assert row["last_latency_ms"] == 120
        assert row["last_checked_at"] is not None

    async def test_paused_monitor_reports_paused_status(self, client, db_session):
        env = await create_team_with_monitor(client, email="pausedstat@x.dev")
        mid = uuid.UUID(env["monitor"]["id"])
        await seed_checks(db_session, mid, [("UP", 120, 2)])
        await client.post(f"{API}/monitors/{mid}/pause", headers=bearer(env["auth"]))

        resp = await client.get(f"{API}/monitors", headers=bearer(env["auth"]))
        row = resp.json()["data"][0]
        assert row["current_status"] == "PAUSED"
