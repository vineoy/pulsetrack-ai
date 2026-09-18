"""Phase 6 tests: prompt builders (no network), Gemini caller (mocked transport),
cache-first analyze (0 real calls on repeat), 429 fallback, team isolation,
rate limiting, and ask grounding."""

import uuid
from datetime import UTC, datetime

import httpx
import pytest

from app.core.exceptions import AppError
from app.core.rate_limit import check_rate_limit
from app.models.check import Check
from app.models.monitor import Monitor
from app.services import ai_service

API = "/api/v1"


@pytest.fixture(autouse=True)
def _reset_ai_client():
    yield
    ai_service.set_client_for_testing(None)


def gemini_transport(text="Root cause: test failure.", calls=None, status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request.url.path)
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "slow down"}})
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": text}]}}],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 5,
                    "totalTokenCount": 15,
                },
            },
        )

    return httpx.MockTransport(handler)


async def register(client, email="owner@ai.dev", team="AI Co"):
    resp = await client.post(
        f"{API}/auth/register",
        json={"name": "Owner One", "team_name": team, "email": email, "password": "Secret123!"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    return data, {"Authorization": f"Bearer {data['access_token']}"}


async def open_incident(client, db_session, headers, name="Site"):
    mon = await client.post(
        f"{API}/monitors",
        json={"name": name, "url": "https://example.com", "interval_min": 1},
        headers=headers,
    )
    assert mon.status_code == 201, mon.text
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
    assert incident is not None
    return str(incident.id)


class TestPromptBuilders:
    def test_analyze_uses_only_first_20_checks(self):
        checks = [
            {"at": f"t{i}", "code": 500, "latency": 10, "error": "boom"} for i in range(30)
        ]
        prompt = ai_service.build_analyze_prompt("S", "https://s.dev", checks)
        assert "t0" in prompt and "t19" in prompt
        assert "t20" not in prompt  # history never leaks into the prompt
        assert "150 words" in prompt

    def test_ask_grounded_on_history(self):
        prompt = ai_service.build_ask_prompt(
            "why down?",
            [{"monitor_name": "Shop", "status": "OPEN", "started_at": "x", "ai_summary": None,
              "error": None}],
        )
        assert "why down?" in prompt and "Shop" in prompt

    def test_ask_never_refuses_uses_general_knowledge(self):
        prompt = ai_service.build_ask_prompt("give me a solution", [])
        assert "Never refuse" in prompt
        assert "general" in prompt.lower()


class TestCallGemini:
    async def test_no_key_returns_error_without_network(self, monkeypatch):
        monkeypatch.setattr(ai_service, "get_api_key", lambda: "")
        text, error, usage = await ai_service.call_gemini("hi")
        assert text is None and "not configured" in error and usage == {}

    async def test_429_maps_to_quota(self):
        ai_service.set_client_for_testing(httpx.AsyncClient(transport=gemini_transport(status=429)))
        text, error, _ = await ai_service.call_gemini("hi")
        assert text is None and error == "quota"

    async def test_success_returns_text_and_usage(self):
        ai_service.set_client_for_testing(httpx.AsyncClient(transport=gemini_transport("Hello")))
        text, error, usage = await ai_service.call_gemini("hi")
        assert text == "Hello" and error is None and usage["total_tokens"] == 15


class TestAnalyzeEndpoints:
    async def test_first_call_hits_gemini_second_is_cached(self, client, db_session, redis_client):
        _, headers = await register(client)
        iid = await open_incident(client, db_session, headers)
        calls: list = []
        ai_service.set_client_for_testing(httpx.AsyncClient(transport=gemini_transport(calls=calls)))

        first = await client.post(f"{API}/incidents/{iid}/analyze", headers=headers)
        assert first.status_code == 200, first.text
        assert first.json()["data"] == {"summary": "Root cause: test failure.", "cached": False}
        assert len(calls) == 1

        # Swap in a failing transport: a cache hit must not touch it.
        ai_service.set_client_for_testing(httpx.AsyncClient(transport=gemini_transport(status=500)))
        second = await client.post(f"{API}/incidents/{iid}/analyze", headers=headers)
        assert second.json()["data"]["cached"] is True

        cached = await client.get(f"{API}/incidents/{iid}/analysis", headers=headers)
        assert cached.status_code == 200 and cached.json()["data"]["cached"] is True

    async def test_analysis_missing_returns_404(self, client, db_session, redis_client):
        _, headers = await register(client, email="a2@ai.dev", team="AI Two")
        iid = await open_incident(client, db_session, headers)
        resp = await client.get(f"{API}/incidents/{iid}/analysis", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "AI_NO_ANALYSIS"

    async def test_gemini_500_without_cache_returns_502(self, client, db_session, redis_client):
        _, headers = await register(client, email="a3@ai.dev", team="AI Three")
        iid = await open_incident(client, db_session, headers)
        ai_service.set_client_for_testing(httpx.AsyncClient(transport=gemini_transport(status=500)))
        resp = await client.post(f"{API}/incidents/{iid}/analyze", headers=headers)
        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "AI_FAILED"

    async def test_cross_team_analyze_is_404(self, client, db_session, redis_client):
        _, headers = await register(client, email="a4@ai.dev", team="AI Four")
        iid = await open_incident(client, db_session, headers)
        await register(client, email="intruder@ai.dev", team="Evil Corp")
        evil = await client.post(
            f"{API}/auth/login", json={"email": "intruder@ai.dev", "password": "Secret123!"}
        )
        evil_headers = {"Authorization": f"Bearer {evil.json()['data']['access_token']}"}
        resp = await client.post(f"{API}/incidents/{iid}/analyze", headers=evil_headers)
        assert resp.status_code == 404

    async def test_rate_limit_blocks_11th_call(self, client, db_session, redis_client):
        _, headers = await register(client, email="a6@ai.dev", team="AI Six")
        iid = await open_incident(client, db_session, headers)
        ai_service.set_client_for_testing(httpx.AsyncClient(transport=gemini_transport()))
        for _ in range(10):
            resp = await client.post(f"{API}/incidents/{iid}/analyze", headers=headers)
            assert resp.status_code == 200
        blocked = await client.post(f"{API}/incidents/{iid}/analyze", headers=headers)
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "RATE_LIMITED"


class TestAsk:
    async def test_no_incidents_answers_without_gemini(self, client, redis_client):
        _, headers = await register(client, email="q@ai.dev", team="Quiet Co")
        calls: list = []
        ai_service.set_client_for_testing(httpx.AsyncClient(transport=gemini_transport(calls=calls)))
        resp = await client.post(f"{API}/ai/ask", json={"question": "Why down?"}, headers=headers)
        assert resp.status_code == 200
        assert "No incidents" in resp.json()["data"]["answer"]
        assert calls == []

    async def test_ask_uses_team_history(self, client, db_session, redis_client):
        _, headers = await register(client, email="q2@ai.dev", team="Noisy Co")
        await open_incident(client, db_session, headers, name="Checkout")
        mock = httpx.AsyncClient(transport=gemini_transport("Because X"))
        ai_service.set_client_for_testing(mock)
        resp = await client.post(
            f"{API}/ai/ask", json={"question": "Why was Checkout down?"}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["answer"] == "Because X"


class TestRateLimiter:
    async def test_allows_then_blocks(self, redis_client):
        for _ in range(3):
            await check_rate_limit(redis_client, key="rl:test", limit=3, window_sec=60)
        with pytest.raises(AppError) as exc:
            await check_rate_limit(redis_client, key="rl:test", limit=3, window_sec=60)
        assert exc.value.status_code == 429
