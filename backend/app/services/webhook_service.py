"""Signed incident delivery to user URLs (Phase 7).

Signing: HMAC_SHA256(secret, "<timestamp>.<body>") hex → X-Signature,
plus X-Timestamp (unix seconds). Receivers recompute and compare, and
reject timestamps older than 5 min (replay protection).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import httpx

TIMEOUT_SECONDS = 10.0
MAX_RETRIES = 3
BACKOFF_SECONDS = [30, 120, 600]
REPLAY_SKEW_SECONDS = 300

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(TIMEOUT_SECONDS, connect=5.0),
            headers={"User-Agent": "PulseTrackAI/0.1 (+outbound-webhooks)"},
            follow_redirects=False,
        )
    return _client


def set_client_for_testing(client: httpx.AsyncClient | None) -> None:
    global _client
    _client = client


def sign_payload(secret: str, timestamp: int, body: bytes) -> str:
    msg = f"{timestamp}.".encode() + body
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def verify_signature(secret: str, timestamp: int, body: bytes, signature: str) -> bool:
    """Receiver-side check (also unit-tested here so users can copy it)."""
    if abs(time.time() - timestamp) > REPLAY_SKEW_SECONDS:
        return False
    return hmac.compare_digest(sign_payload(secret, timestamp, body), signature)


def build_event(
    event: str, *, team_slug: str, monitor_name: str, monitor_url: str, incident: dict
) -> dict:
    return {
        "event": event,  # incident.opened | incident.resolved | incident.opened (test)
        "team": {"slug": team_slug},
        "monitor": {"name": monitor_name, "url": monitor_url},
        "incident": incident,
        "at": int(time.time()),
    }


async def deliver(url: str, secret: str, payload: dict) -> tuple[bool, str | None, int | None]:
    """POST signed JSON with retries. Returns (ok, error, http_status). Never raises."""
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    last_error: str | None = None
    last_status: int | None = None
    for attempt in range(MAX_RETRIES):
        timestamp = int(time.time())
        body = json.dumps({**payload, "at": timestamp}, separators=(",", ":")).encode("utf-8")
        try:
            resp = await _get_client().post(
                url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Signature": sign_payload(secret, timestamp, body),
                    "X-Timestamp": str(timestamp),
                },
            )
            last_status = resp.status_code
            if 200 <= resp.status_code < 300:
                return True, None, resp.status_code
            last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except httpx.TimeoutException:
            last_error = f"webhook timeout after {TIMEOUT_SECONDS:.0f}s"
        except httpx.HTTPError as exc:
            last_error = f"webhook network error: {type(exc).__name__}"
        except Exception:  # noqa: BLE001
            last_error = "webhook unexpected error"
        if attempt < MAX_RETRIES - 1:
            import asyncio

            await asyncio.sleep(BACKOFF_SECONDS[attempt])
    return False, last_error, last_status
