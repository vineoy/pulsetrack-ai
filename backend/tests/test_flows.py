"""Phase 8 gap-fill: maintenance windows, incident ack flows, system endpoints."""

from datetime import UTC, datetime, timedelta

from tests.test_auth import API, bearer, register_user


def window_body(hours=1):
    now = datetime.now(UTC)
    return {
        "monitor_id": None,
        "starts_at": (now - timedelta(minutes=1)).isoformat(),
        "ends_at": (now + timedelta(hours=hours)).isoformat(),
        "reason": "deploy",
    }


class TestMaintenance:
    async def test_crud_and_validation(self, client):
        owner = await register_user(client, email="mt@x.dev", team_name="Mt Co")
        headers = bearer(owner)
        created = await client.post(f"{API}/maintenance", json=window_body(), headers=headers)
        assert created.status_code == 201, created.text
        listed = await client.get(f"{API}/maintenance", headers=headers)
        assert len(listed.json()["data"]) == 1
        bad = await client.post(
            f"{API}/maintenance",
            json={**window_body(), "ends_at": (datetime.now(UTC) - timedelta(hours=2)).isoformat()},
            headers=headers,
        )
        assert bad.status_code == 422
        wid = created.json()["data"]["id"]
        evil = await register_user(client, email="mt-evil@x.dev", team_name="Mt Evil")
        assert (
            await client.delete(f"{API}/maintenance/{wid}", headers=bearer(evil))
        ).status_code == 404
        assert (await client.delete(f"{API}/maintenance/{wid}", headers=headers)).status_code == 200

    async def test_per_monitor_window_rejects_foreign_monitor(self, client):
        owner = await register_user(client, email="mt2@x.dev", team_name="Mt Two")
        headers = bearer(owner)
        evil = await register_user(client, email="mt2-evil@x.dev", team_name="Mt Two Evil")
        mon = await client.post(
            f"{API}/monitors",
            json={"name": "S", "url": "https://example.com", "interval_min": 1},
            headers=bearer(evil),
        )
        body = window_body()
        body["monitor_id"] = mon.json()["data"]["id"]
        resp = await client.post(f"{API}/maintenance", json=body, headers=headers)
        assert resp.status_code in (404, 422)


class TestIncidentFlows:
    async def test_list_get_ack_and_double_ack(self, client, db_session):
        owner = await register_user(client, email="iff@x.dev", team_name="Iff Co")
        headers = bearer(owner)
        mon = await client.post(
            f"{API}/monitors",
            json={"name": "S", "url": "https://example.com", "interval_min": 1},
            headers=headers,
        )
        mid = mon.json()["data"]["id"]
        from datetime import UTC as _UTC
        from uuid import UUID

        from app.models.check import Check
        from app.models.monitor import Monitor
        from app.services.incident_service import apply_flap_logic

        for _ in range(2):
            db_session.add(
                Check(
                    monitor_id=UUID(mid),
                    status="DOWN",
                    status_code=500,
                    checked_at=datetime.now(_UTC),
                )
            )
        await db_session.commit()
        monitor = await db_session.get(Monitor, UUID(mid))
        incident = await apply_flap_logic(db_session, monitor)
        await db_session.commit()
        iid = str(incident.id)

        all_incidents = await client.get(f"{API}/incidents", headers=headers)
        assert len(all_incidents.json()["data"]) == 1
        open_only = await client.get(
            f"{API}/incidents", params={"status": "OPEN"}, headers=headers
        )
        assert len(open_only.json()["data"]) == 1
        assert (await client.get(f"{API}/incidents/{iid}", headers=headers)).status_code == 200
        acked = await client.post(f"{API}/incidents/{iid}/acknowledge", headers=headers)
        assert acked.status_code == 200 and acked.json()["data"]["status"] == "ACK"
        again = await client.post(f"{API}/incidents/{iid}/acknowledge", headers=headers)
        assert again.status_code == 400
        by_monitor = await client.get(f"{API}/incidents/by-monitor/{mid}", headers=headers)
        assert len(by_monitor.json()["data"]) == 1
        evil = await register_user(client, email="iff-evil@x.dev", team_name="Iff Evil")
        assert (
            await client.get(f"{API}/incidents/{iid}", headers=bearer(evil))
        ).status_code == 404


class TestSystem:
    async def test_root_and_health(self, client):
        root = await client.get("/")
        assert root.status_code == 200 and "docs" in root.json()
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] in ("ok", "degraded")
