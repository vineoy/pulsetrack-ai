"""Gemini AI analyst (Phase 6) — root-cause explanations, customer drafts, Q&A.

Quota rules (roadmap section 13):
1) Cache 24h (`ai:{incident_id}`, `ai:draft:{id}:{tone}`) — repeat clicks cost $0.
2) Never call in the scheduler/check loop — only on human click (endpoints below).
3) 429/timeout → graceful "AI busy" fallback. AI failures never break incidents.

Uses the Gemini v1beta REST API (generateContent) via httpx. Never raises:
call_gemini returns (text, error, usage) tuples like telegram_service.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger("pulsetrack.ai")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com"
REQUEST_TIMEOUT_SECONDS = 20.0
TEMPERATURE = 0.2
MAX_OUTPUT_TOKENS = 400
CACHE_TTL_SECONDS = 24 * 60 * 60

# Swap in tests: MockTransport-backed client
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS, connect=5.0),
            headers={"User-Agent": "PulseTrackAI/0.1 (+ai-analyst)"},
        )
    return _client


def set_client_for_testing(client: httpx.AsyncClient | None) -> None:
    global _client
    _client = client


def get_api_key() -> str:
    return get_settings().gemini_api_key.strip()


def get_model() -> str:
    return get_settings().gemini_model.strip() or "gemini-3.5-flash-lite"


def analysis_key(incident_id: object) -> str:
    return f"ai:{incident_id}"


# ---------- Pure prompt builders (unit-testable, zero network) ----------


def build_analyze_prompt(
    monitor_name: str, monitor_url: str, checks: list[dict]
) -> str:
    """Root-cause prompt. Only the last 20 checks (~800 tokens), never history."""
    rows = "\n".join(
        f"- {c.get('at')}: code={c.get('code')} latency={c.get('latency')}ms "
        f"error={c.get('error') or '-'}"
        for c in checks[:20]
    )
    return (
        f"You are a senior SRE. Monitor '{monitor_name}' ({monitor_url}) went DOWN.\n"
        f"Last checks (newest first):\n{rows}\n\n"
        "Return exactly:\n"
        "1) Likely cause in 1 line\n"
        "2) Evidence in 2 bullets\n"
        "3) Fix in 3 numbered steps\n"
        "Max 150 words. No guessing beyond the data above. "
        "If SSL/cert errors appear, mention them first."
    )


def build_ask_prompt(question: str, incidents: list[dict]) -> str:
    context = "\n".join(
        f"- {i.get('monitor_name')} [{i.get('status')}] started {i.get('started_at')}: "
        f"{(i.get('ai_summary') or i.get('error') or 'no details')[:300]}"
        for i in incidents[:5]
    )
    return (
        "You are a senior SRE helping this team with their outages. "
        "Their incident history (primary context):\n"
        f"{context}\n\n"
        f"Question: {question}\n"
        "Answer in max 150 words. Use the history first — cite its facts when relevant. "
        "When the history lacks the answer, use your general SRE knowledge to give "
        "accurate, actionable steps anyway (say briefly which parts come from general "
        "knowledge). Never refuse: always give the most useful answer you can."
    )


# ---------- REST caller (never raises) ----------


async def call_gemini(prompt: str) -> tuple[str | None, str | None, dict]:
    """One Gemini call. Returns (text, error, usage). Never raises."""
    key = get_api_key()
    if not key:
        return None, "GEMINI_API_KEY is not configured on the server", {}
    url = f"{GEMINI_API_BASE}/v1beta/models/{get_model()}:generateContent"
    try:
        resp = await _get_client().post(
            url,
            params={"key": key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": TEMPERATURE,
                    "maxOutputTokens": MAX_OUTPUT_TOKENS,
                },
            },
        )
    except httpx.TimeoutException:
        return None, "AI timed out after 20s — retry shortly", {}
    except httpx.HTTPError as exc:
        return None, f"AI network error: {type(exc).__name__}", {}
    except Exception:  # noqa: BLE001
        return None, "AI unexpected error", {}

    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        body = {}
    if resp.status_code == 429:
        return None, "quota", {}
    if resp.status_code != 200 or "candidates" not in body:
        detail = ""
        try:
            detail = str(body.get("error", {}).get("message", ""))[:150]
        except (AttributeError, TypeError):
            pass
        return None, f"AI error {resp.status_code}: {detail}", {}
    try:
        text = body["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        return None, "AI returned an empty answer — retry shortly", {}
    usage: dict = {}
    try:
        meta = body.get("usageMetadata") or {}
        usage = {
            "prompt_tokens": int(meta.get("promptTokenCount", 0)),
            "output_tokens": int(meta.get("candidatesTokenCount", 0)),
            "total_tokens": int(meta.get("totalTokenCount", 0)),
        }
    except (ValueError, TypeError):
        usage = {}
    if usage:
        logger.info("gemini call tokens=%s model=%s", usage, get_model())
    if not text:
        return None, "AI returned an empty answer — retry shortly", usage
    return text, None, usage


# ---------- Orchestration (cache-first, DB-backed, never raises into HTTP) ----------


async def analyze_for_incident(db, redis, incident, monitor) -> dict:
    """Explain an incident. Returns {summary, cached, error, tokens}.

    Order: Redis ai:{id} → Postgres ai_summary → 1 Gemini call → save both.
    `error` is a human message when AI couldn't produce a fresh answer
    (quota/timeout/no key) — HTTP layer decides the status code.
    """
    from app.repositories import check_repository

    key = analysis_key(incident.id)
    hit = await cache_get(redis, key)
    if hit:
        return {"summary": hit, "cached": True, "error": None, "tokens": {}}
    if incident.ai_summary:
        await cache_set(redis, key, incident.ai_summary)
        return {"summary": incident.ai_summary, "cached": True, "error": None, "tokens": {}}

    checks = await check_repository.recent_for_monitor(db, monitor.id, limit=20)
    rows = [
        {
            "at": c.checked_at.isoformat() if c.checked_at else "-",
            "code": c.status_code,
            "latency": c.latency_ms,
            "error": c.error,
        }
        for c in checks
    ]
    text, error, usage = await call_gemini(build_analyze_prompt(monitor.name, monitor.url, rows))
    if text:
        incident.ai_summary = text
        await db.commit()
        await cache_set(redis, key, text)
        return {"summary": text, "cached": False, "error": None, "tokens": usage}
    if error == "quota":
        error = "AI quota is busy right now (free tier) — retry in a minute"
    return {
        "summary": incident.ai_summary,
        "cached": incident.ai_summary is not None,
        "error": error,
        "tokens": usage,
    }


# ---------- Cache helpers (Redis injected, test-friendly) ----------


async def cache_get(redis, key: str) -> str | None:
    try:
        raw = await redis.get(key)
    except Exception:  # noqa: BLE001
        return None
    return str(raw) if raw else None


async def cache_set(redis, key: str, value: str, ttl: int = CACHE_TTL_SECONDS) -> None:
    try:
        await redis.set(key, value, ex=ttl)
    except Exception:  # noqa: BLE001
        pass
