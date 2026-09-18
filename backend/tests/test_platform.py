"""Phase 7 tests: API keys (hash-only, roles, revoke), HMAC webhooks
(sign/verify/replay/test/delivery job), audit reader (owner-only, filters)."""

import json
import time
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select

from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.models.check import Check
from app.models.monitor import Monitor
from app.services import webhook_service
from app.workers.webhooker import webhook_delivery_job

API = "/api/v1"


async def register(client, email="owner@p.dev", team="Plat Co", password="Secret123!"):
    resp = await client.post(
        f"{API}/auth/register",
        json={"name": "Owner One", "team_name": team, "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    return data, {"Authorization": f"Bearer {data['access_token']}"}


async def invite_member(client, owner_headers, email="member@p.dev"):
    resp = await client.post(
        f"{API}/teams/invite", json={"email": email, "role": "member"}, headers=owner_headers
    )
    assert resp.status_code == 201, resp.text
    temp = resp.json()["data"]["temp_password"]
    login = await client.post(f"{API}/auth/login", json={"email": email, "password": temp})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


class TestApiKeys:
    async def test_mint_shows_raw_once_and_stores_hash_only(
        self, client, db_session, redis_client
    ):
        _, headers = await register(client)
        resp = await client.post(f"{API}/api-keys", json={"name": "CI"}, headers=headers)
        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["key"].startswith("pk_live_")
        assert data["prefix"] == data["key"][:12]

        row = (await db_session.execute(select(ApiKey))).scalar_one()
        assert row.prefix == data["key"][:12]
        assert row.key_hash != data["key"]  # fingerprint only
        assert len(row.key_hash) == 64

    async def test_key_authenticates_and_inherits_owner_role(
        self, client, db_session, redis_client
    ):
        _, headers = await register(client, email="k2@p.dev", team="Key Two")
        raw = (await client.post(f"{API}/api-keys", json={"name": "CI"}, headers=headers)).json()[
            "data"
        ]["key"]
        key_headers = {"Authorization": f"Bearer {raw}"}
        me = await client.get(f"{API}/auth/me", headers=key_headers)
        assert me.status_code == 200
        mon = await client.post(
            f"{API}/monitors",
            json={"name": "ViaKey", "url": "https://example.com", "interval_min": 5},
            headers=key_headers,
        )
        assert mon.status_code == 201

    async def test_owner_key_inherits_owner_powers(self, client, db_session, redis_client):
        # Only owners mint (roadmap), so keys carry owner role: DELETE works.
        _, owner_headers = await register(client, email="k3@p.dev", team="Key Three")
        raw = (
            await client.post(f"{API}/api-keys", json={"name": "CI"}, headers=owner_headers)
        ).json()["data"]["key"]
        key_headers = {"Authorization": f"Bearer {raw}"}
        mon = await client.post(
            f"{API}/monitors",
            json={"name": "M", "url": "https://example.com", "interval_min": 5},
            headers=owner_headers,
        )
        mid = mon.json()["data"]["id"]
        deleted = await client.delete(f"{API}/monitors/{mid}", headers=key_headers)
        assert deleted.status_code == 200

    async def test_member_cannot_mint_keys(self, client, db_session, redis_client):
        _, owner_headers = await register(client, email="k3b@p.dev", team="Key Three B")
        member_headers = await invite_member(client, owner_headers, email="m3b@p.dev")
        resp = await client.post(f"{API}/api-keys", json={"name": "M"}, headers=member_headers)
        assert resp.status_code == 403

    async def test_unknown_and_revoked_keys_are_401(self, client, db_session, redis_client):
        _, headers = await register(client, email="k4@p.dev", team="Key Four")
        bad = await client.get(f"{API}/auth/me", headers={"Authorization": "Bearer pk_live_nope"})
        assert bad.status_code == 401
        raw = (await client.post(f"{API}/api-keys", json={"name": "X"}, headers=headers)).json()[
            "data"
        ]["key"]
        kid = (await db_session.execute(select(ApiKey))).scalar_one().id
        await client.delete(f"{API}/api-keys/{kid}", headers=headers)
        gone = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {raw}"})
        assert gone.status_code == 401

    async def test_member_cannot_mint_or_list_keys(self, client, db_session, redis_client):
        _, owner_headers = await register(client, email="k5@p.dev", team="Key Five")
        member_headers = await invite_member(client, owner_headers, email="m5@p.dev")
        assert (
            await client.post(f"{API}/api-keys", json={"name": "X"}, headers=member_headers)
        ).status_code == 403
        assert (await client.get(f"{API}/api-keys", headers=member_headers)).status_code == 403


class TestHmac:
    def test_sign_verify_roundtrip(self):
        body = b'{"event":"incident.opened"}'
        ts = int(time.time())
        sig = webhook_service.sign_payload("s3cret", ts, body)
        assert webhook_service.verify_signature("s3cret", ts, body, sig) is True

    def test_wrong_secret_tampered_and_stale_rejected(self):
        body = b'{"event":"incident.opened"}'
        ts = int(time.time())
        sig = webhook_service.sign_payload("s3cret", ts, body)
        assert webhook_service.verify_signature("other", ts, body, sig) is False
        assert webhook_service.verify_signature("s3cret", ts, b"{}", sig) is False
        stale = webhook_service.sign_payload("s3cret", ts - 9999, body)
        assert webhook_service.verify_signature("s3cret", ts - 9999, body, stale) is False


class TestWebhooks:
    async def test_crud_and_test_delivery(self, client, db_session, redis_client):
        from app.services import webhook_service as ws

        seen: list = []

        def handler(req: httpx.Request) -> httpx.Response:
            seen.append(req)
            return httpx.Response(200, json={"ok": True})

        ws.set_client_for_testing(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        try:
            _, headers = await register(client, email="w@p.dev", team="Hook Co")
            bad = await client.post(
                f"{API}/webhooks/outbound", json={"url": "not-a-url"}, headers=headers
            )
            assert bad.status_code == 422
            created = await client.post(
                f"{API}/webhooks/outbound", json={"url": "https://example.com/h"}, headers=headers
            )
            assert created.status_code == 201, created.text
            assert created.json()["data"]["secret"].startswith("whsec_")
            wid = created.json()["data"]["id"]
            listed = await client.get(f"{API}/webhooks/outbound", headers=headers)
            assert "secret" not in listed.json()["data"][0]

            tested = await client.post(f"{API}/webhooks/outbound/{wid}/test", headers=headers)
            assert tested.json()["data"]["ok"] is True
            assert len(seen) == 1
            payload = json.loads(seen[0].content)
            assert payload["event"] == "incident.opened"
            assert seen[0].headers["x-signature"]
        finally:
            ws.set_client_for_testing(None)

    async def test_delivery_job_sends_open_and_logs_audit(
        self, client, db_session, redis_client
    ):
        from app.services import webhook_service as ws

        ws.set_client_for_testing(
            httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200)))
        )
        try:
            _, headers = await register(client, email="w2@p.dev", team="Hook Two")
            await client.post(
                f"{API}/webhooks/outbound", json={"url": "https://example.com/h"}, headers=headers
            )
            mon = await client.post(
                f"{API}/monitors",
                json={"name": "S", "url": "https://example.com", "interval_min": 1},
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

            # Point the job at the TEST database.
            from sqlalchemy.ext.asyncio import async_sessionmaker

            import app.workers.webhooker as webhooker

            webhooker.async_session_factory = async_sessionmaker(
                db_session.bind, expire_on_commit=False
            )
            result = await webhook_delivery_job({}, str(incident.id), "open")
            assert "delivered=1/1" in result
            audits = (
                await db_session.execute(
                    select(AuditLog).where(AuditLog.action == "webhook.delivered")
                )
            ).scalars().all()
            assert len(audits) == 1
            assert audits[0].detail["event"] == "incident.opened"
        finally:
            ws.set_client_for_testing(None)


class TestAuditReader:
    async def test_owner_lists_member_denied_and_filter_works(
        self, client, db_session, redis_client
    ):
        _, owner_headers = await register(client, email="a@p.dev", team="Audit Co")
        member_headers = await invite_member(client, owner_headers, email="am@p.dev")
        await client.post(
            f"{API}/monitors",
            json={"name": "S", "url": "https://example.com", "interval_min": 5},
            headers=owner_headers,
        )
        denied = await client.get(f"{API}/audit-logs", headers=member_headers)
        assert denied.status_code == 403
        page = await client.get(f"{API}/audit-logs", headers=owner_headers)
        assert page.status_code == 200
        assert page.json()["data"]["total"] >= 1
        filtered = await client.get(
            f"{API}/audit-logs", params={"action": "monitor.created"}, headers=owner_headers
        )
        items = filtered.json()["data"]["items"]
        assert items and all(i["action"] == "monitor.created" for i in items)
