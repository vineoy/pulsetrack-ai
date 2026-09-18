"""Phase 8 gap-fill: CSV exports (content, caps, filters, tenancy)."""

import uuid
from datetime import UTC, datetime

from tests.test_auth import API, bearer, register_user


async def seed_checks(db_session, monitor_id, n, status="UP"):
    from app.models.check import Check

    for _i in range(n):
        db_session.add(
            Check(
                monitor_id=monitor_id,
                status=status,
                latency_ms=120,
                status_code=200 if status == "UP" else 500,
                error="x, y\nz" if status == "DOWN" else None,  # quoting proof
                checked_at=datetime.now(UTC),
            )
        )
    await db_session.commit()


class TestChecksExport:
    async def test_header_rows_quoting_and_disposition(self, client, db_session):
        owner = await register_user(client, email="ex@x.dev", team_name="Export Co")
        headers = bearer(owner)
        mid = (
            await client.post(
                f"{API}/monitors",
                json={"name": "S", "url": "https://example.com", "interval_min": 1},
                headers=headers,
            )
        ).json()["data"]["id"]
        await seed_checks(db_session, uuid.UUID(mid), 3, "UP")
        await seed_checks(db_session, uuid.UUID(mid), 2, "DOWN")
        resp = await client.get(f"{API}/monitors/{mid}/checks/export", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        disposition = resp.headers["content-disposition"]
        assert disposition.startswith("attachment; filename=pulsetrack-checks-")
        import csv
        import io

        rows = list(csv.reader(io.StringIO(resp.text)))
        assert rows[0] == ["checked_at", "status", "latency_ms", "status_code", "error"]
        assert len(rows) == 6  # header + 5 rows, newest first
        assert any("x, y\nz" in r[4] for r in rows[1:])  # comma/newline survived round-trip

    async def test_date_filters_and_cross_team_404(self, client, db_session):
        from datetime import timedelta

        owner = await register_user(client, email="ex2@x.dev", team_name="Export Two")
        headers = bearer(owner)
        mid = (
            await client.post(
                f"{API}/monitors",
                json={"name": "S", "url": "https://example.com", "interval_min": 1},
                headers=headers,
            )
        ).json()["data"]["id"]
        await seed_checks(db_session, uuid.UUID(mid), 2, "UP")
        future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        empty = await client.get(
            f"{API}/monitors/{mid}/checks/export", params={"from": future}, headers=headers
        )
        assert empty.text.strip().splitlines() == [
            "checked_at,status,latency_ms,status_code,error"
        ]
        evil = await register_user(client, email="ex-evil@x.dev", team_name="Export Evil")
        assert (
            await client.get(f"{API}/monitors/{mid}/checks/export", headers=bearer(evil))
        ).status_code == 404


class TestIncidentsExport:
    async def test_header_status_filter_and_isolation(self, client, db_session):
        owner = await register_user(client, email="ex3@x.dev", team_name="Export Three")
        headers = bearer(owner)
        mid = (
            await client.post(
                f"{API}/monitors",
                json={"name": "S", "url": "https://example.com", "interval_min": 1},
                headers=headers,
            )
        ).json()["data"]["id"]
        await seed_checks(db_session, uuid.UUID(mid), 2, "DOWN")
        from app.models.monitor import Monitor
        from app.services.incident_service import apply_flap_logic

        monitor = await db_session.get(Monitor, uuid.UUID(mid))
        assert await apply_flap_logic(db_session, monitor) is not None
        await db_session.commit()

        resp = await client.get(f"{API}/incidents/export", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-disposition"] == (
            "attachment; filename=pulsetrack-incidents.csv"
        )
        lines = resp.text.strip().splitlines()
        assert lines[0] == "id,monitor,status,started_at,resolved_at,downtime_min"
        assert len(lines) == 2 and ",S,OPEN," in lines[1]

        resolved_only = await client.get(
            f"{API}/incidents/export", params={"status": "RESOLVED"}, headers=headers
        )
        assert resolved_only.text.strip().splitlines() == [
            "id,monitor,status,started_at,resolved_at,downtime_min"
        ]
        evil = await register_user(client, email="ex3-evil@x.dev", team_name="Export E3")
        other = await client.get(f"{API}/incidents/export", headers=bearer(evil))
        assert other.text.strip().splitlines() == [
            "id,monitor,status,started_at,resolved_at,downtime_min"
        ]
