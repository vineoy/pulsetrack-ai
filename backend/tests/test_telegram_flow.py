"""Phase 8 gap-fill: Telegram sender, link tokens, channels CRUD, auto-connect flow."""

import uuid

import httpx
import pytest
from sqlalchemy import select

from app.models.notification_channel import NotificationChannel
from app.services import telegram_link_service as link_service
from app.services import telegram_service as tg
from tests.test_auth import API, bearer, register_user

OK_BODY = {"ok": True, "result": {"message_id": 7}}


def transport(handler):
    return httpx.MockTransport(handler)


def _factory(db_session):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    return async_sessionmaker(db_session.bind, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _reset_tg_client():
    yield
    tg.set_client_for_testing(None)


class TestSendMessage:
    async def test_ok_returns_message_id(self):
        tg.set_client_for_testing(
            httpx.AsyncClient(transport=transport(lambda r: httpx.Response(200, json=OK_BODY)))
        )
        ok, error, msg_id = await tg.send_message("123", "hi")
        assert (ok, error, msg_id) == (True, None, 7)

    async def test_missing_token_short_circuits(self, monkeypatch):
        monkeypatch.setattr(tg, "get_bot_token", lambda: "")
        ok, error, msg_id = await tg.send_message("123", "hi")
        assert ok is False and "not configured" in error and msg_id is None

    async def test_429_then_ok(self):
        calls = []

        def handler(request):
            calls.append(1)
            if len(calls) == 1:
                return httpx.Response(
                    429, json={"ok": False, "parameters": {"retry_after": 0}}
                )
            return httpx.Response(200, json=OK_BODY)

        tg.set_client_for_testing(httpx.AsyncClient(transport=transport(handler)))
        ok, _, _ = await tg.send_message("123", "hi")
        assert ok is True and len(calls) == 2

    async def test_500_gives_error_not_raise(self):
        tg.set_client_for_testing(
            httpx.AsyncClient(
                transport=transport(lambda r: httpx.Response(500, text="boom"))
            )
        )
        ok, error, msg_id = await tg.send_message("123", "hi")
        assert ok is False and error and msg_id is None

    async def test_timeout_gives_error(self):
        def handler(request):
            raise httpx.ConnectTimeout("slow", request=request)

        tg.set_client_for_testing(httpx.AsyncClient(transport=transport(handler)))
        ok, error, _ = await tg.send_message("123", "hi")
        assert ok is False and "timeout" in error.lower()

    def test_builders_and_deep_link(self):
        assert "DOWN" in tg.build_open_message("S", "https://s.dev", "incident-id-123")
        assert "RECOVERED" in tg.build_recovery_message("S", "https://s.dev", 3)
        assert "STILL DOWN" in tg.build_escalation_message("S", "https://s.dev", "iid")
        assert "test OK" in tg.build_test_message("S") and "test OK" in tg.build_test_message(None)
        assert "connected" in tg.build_connected_message("Team").lower()
        assert tg.parse_start_payload("/start abc123") == "abc123"
        assert tg.parse_start_payload("/start") is None
        assert tg.parse_start_payload("hello") is None
        assert tg.parse_start_payload(None) is None


class TestLinkTokens:
    async def test_create_get_consume_done_offset(self, redis_client):
        team, user = uuid.uuid4(), uuid.uuid4()
        link = await link_service.create_link(redis_client, team_id=team, user_id=user, label="DM")
        assert link["expires_in_sec"] == 15 * 60
        got = await link_service.get_link(redis_client, link["token"])
        assert got["team_id"] == str(team) and got["label"] == "DM"
        consumed = await link_service.consume_link(redis_client, link["token"])
        assert consumed["user_id"] == str(user)
        assert await link_service.get_link(redis_client, link["token"]) is None
        assert await link_service.get_connected_channel_id(redis_client, link["token"]) is None
        await link_service.mark_connected(redis_client, link["token"], uuid.uuid4())
        assert await link_service.get_connected_channel_id(redis_client, link["token"])
        assert await link_service.get_offset(redis_client) is None
        await link_service.set_offset(redis_client, 42)
        assert await link_service.get_offset(redis_client) == 42
        assert await link_service.cancel_link(redis_client, "nope") is False


class TestChannelsRouter:
    async def test_manual_crud_and_validation(self, client):
        owner = await register_user(client, email="ch@x.dev", team_name="Ch Co")
        headers = bearer(owner)
        bad = await client.post(
            f"{API}/notification-channels", json={"telegram_chat_id": "abc"}, headers=headers
        )
        assert bad.status_code == 422
        created = await client.post(
            f"{API}/notification-channels",
            json={"telegram_chat_id": " 123456 ", "label": "DM"},
            headers=headers,
        )
        assert created.status_code == 201
        assert created.json()["data"]["telegram_chat_id"] == "123456"
        listed = await client.get(f"{API}/notification-channels", headers=headers)
        assert len(listed.json()["data"]) == 1
        other = await register_user(client, email="ch2@x.dev", team_name="Ch Two")
        gone = await client.delete(
            f"{API}/notification-channels/{created.json()['data']['id']}",
            headers=bearer(other),
        )
        assert gone.status_code == 404
        deleted = await client.delete(
            f"{API}/notification-channels/{created.json()['data']['id']}", headers=headers
        )
        assert deleted.status_code == 200

    async def test_test_button_ok_and_failed(self, client, db_session):
        owner = await register_user(client, email="cht@x.dev", team_name="Ch Test")
        headers = bearer(owner)
        created = await client.post(
            f"{API}/notification-channels", json={"telegram_chat_id": "999"}, headers=headers
        )
        cid = created.json()["data"]["id"]
        tg.set_client_for_testing(
            httpx.AsyncClient(transport=transport(lambda r: httpx.Response(200, json=OK_BODY)))
        )
        ok = await client.post(f"{API}/notification-channels/{cid}/test", headers=headers)
        assert ok.status_code == 200
        tg.set_client_for_testing(
            httpx.AsyncClient(transport=transport(lambda r: httpx.Response(403, text="blocked")))
        )
        failed = await client.post(f"{API}/notification-channels/{cid}/test", headers=headers)
        assert failed.status_code == 502
        assert failed.json()["error"]["code"] == "TELEGRAM_FAILED"


class TestAutoConnectFlow:
    async def test_connect_status_cancel_and_cross_team(self, client, redis_client):
        owner = await register_user(client, email="ac@x.dev", team_name="AC Co")
        headers = bearer(owner)
        created = await client.post(
            f"{API}/notification-channels/connect", json={"label": "DM"}, headers=headers
        )
        assert created.status_code == 201
        token = created.json()["data"]["token"]
        assert created.json()["data"]["expires_in_sec"] == 15 * 60
        pending = await client.get(
            f"{API}/notification-channels/connect/{token}/status", headers=headers
        )
        assert pending.json()["data"]["status"] == "pending"
        evil = await register_user(client, email="evil@x.dev", team_name="Evil")
        blocked = await client.get(
            f"{API}/notification-channels/connect/{token}/status", headers=bearer(evil)
        )
        assert blocked.status_code == 404
        cancelled = await client.delete(
            f"{API}/notification-channels/connect/{token}", headers=headers
        )
        assert cancelled.status_code == 200
        expired = await client.get(
            f"{API}/notification-channels/connect/{token}/status", headers=headers
        )
        assert expired.json()["data"]["status"] == "expired"

    async def test_poller_creates_channel_once(
        self, client, db_session, redis_client, monkeypatch
    ):
        import app.workers.telegram_poller as poller

        owner = await register_user(client, email="pl@x.dev", team_name="Poll Co")
        headers = bearer(owner)
        token = (
            await client.post(
                f"{API}/notification-channels/connect", json={"label": "DM"}, headers=headers
            )
        ).json()["data"]["token"]

        monkeypatch.setattr(
            poller, "async_session_factory", _factory(db_session)
        )
        monkeypatch.setattr(poller, "redis_client", redis_client)
        monkeypatch.setattr(tg, "get_bot_token", lambda: "dummy")
        updates = [
            {"update_id": 10, "message": {"text": f"/start {token}", "chat": {"id": 555}}},
            {"update_id": 11, "message": {"text": "hello", "chat": {"id": 555}}},
            {"update_id": 12, "message": {"text": "/start stale-token", "chat": {"id": 555}}},
        ]

        async def fake_updates(offset=None, timeout=0, limit=100):
            return [u for u in updates if offset is None or u["update_id"] >= offset], None

        async def fake_send(chat_id, text, parse_mode="Markdown"):
            return True, None, 1

        monkeypatch.setattr(tg, "get_updates", fake_updates)
        monkeypatch.setattr(tg, "send_message", fake_send)

        assert await poller.poll_telegram_updates({}) == "ok connected=1 scanned=3"
        rows = (
            await db_session.execute(select(NotificationChannel))
        ).scalars().all()
        assert len(rows) == 1 and rows[0].telegram_chat_id == "555"
        done = await client.get(
            f"{API}/notification-channels/connect/{token}/status", headers=headers
        )
        assert done.json()["data"]["status"] == "connected"

        # Same /start again (offset advanced past it) + press Start twice edge:
        # re-inject the same update with a fresh token → dedupe by chat_id, no 2nd row.
        token2 = (
            await client.post(f"{API}/notification-channels/connect", json={}, headers=headers)
        ).json()["data"]["token"]
        updates.append(
            {"update_id": 13, "message": {"text": f"/start {token2}", "chat": {"id": 555}}}
        )
        assert "connected=1" in await poller.poll_telegram_updates({})
        rows = (
            await db_session.execute(select(NotificationChannel))
        ).scalars().all()
        assert len(rows) == 1  # deduped, not duplicated

    async def test_poller_skips_without_token(self, monkeypatch):
        import app.workers.telegram_poller as poller

        monkeypatch.setattr(tg, "get_bot_token", lambda: "")
        assert await poller.poll_telegram_updates({}) == "skipped:no_token"

    async def test_get_updates_missing_token(self, monkeypatch):
        monkeypatch.setattr(tg, "get_bot_token", lambda: "")
        updates, error = await tg.get_updates(None)
        assert updates == [] and "not configured" in error
