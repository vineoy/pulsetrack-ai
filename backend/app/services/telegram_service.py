"""Telegram Bot API sender — the only alert channel.

Uses the global TELEGRAM_BOT_TOKEN (BotFather) + per-team telegram_chat_id.
Retries 3x with exponential backoff; respects 429 Retry-After.
All network errors are returned as (ok=False, error) — never raises into the worker.
"""

import asyncio

import httpx

from app.core.config import get_settings

TELEGRAM_API_BASE = "https://api.telegram.org"
MAX_RETRIES = 3
BACKOFF_SECONDS = [1, 3, 8]

# Swap in tests: MockTransport-backed client
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers={"User-Agent": "PulseTrackAI/0.1 (+telegram-alerts)"},
        )
    return _client


def set_client_for_testing(client: httpx.AsyncClient | None) -> None:
    global _client
    _client = client


def get_bot_token() -> str:
    return get_settings().telegram_bot_token.strip()


def get_bot_username() -> str:
    return get_settings().telegram_bot_username.strip().lstrip("@")


def build_deep_link(token: str) -> str | None:
    """t.me deep link for auto-connect. None when username is not configured."""
    username = get_bot_username()
    if not username:
        return None
    return f"https://t.me/{username}?start={token}"


def parse_start_payload(text: str | None) -> str | None:
    """Extract the connect token from a '/start <token>' message.

    Returns None for plain /start, other commands, or empty text.
    """
    if not text:
        return None
    parts = text.strip().split()
    if not parts or parts[0].split("@")[0] != "/start":
        return None
    if len(parts) < 2:
        return None
    payload = parts[1].strip()
    return payload or None


async def get_updates(
    offset: int | None = None, *, timeout: int = 0, limit: int = 100
) -> tuple[list[dict], str | None]:
    """Long/short-poll getUpdates. Returns (updates, error). Never raises."""
    token = get_bot_token()
    if not token:
        return [], "TELEGRAM_BOT_TOKEN is not configured on the server"
    url = f"{TELEGRAM_API_BASE}/bot{token}/getUpdates"
    params: dict[str, int] = {"limit": max(1, min(limit, 100))}
    if offset is not None:
        params["offset"] = offset
    if timeout:
        params["timeout"] = timeout
    try:
        resp = await _get_client().get(url, params=params)
        ctype = resp.headers.get("content-type", "")
        body = resp.json() if ctype.startswith("application/json") else {}
        if resp.status_code == 200 and body.get("ok"):
            result = body.get("result")
            return result if isinstance(result, list) else [], None
        desc = body.get("description") if isinstance(body, dict) else None
        return [], desc or f"Telegram {resp.status_code}: {resp.text[:200]}"
    except httpx.TimeoutException:
        return [], "Telegram timeout on getUpdates"
    except httpx.HTTPError as exc:
        return [], f"Telegram network error: {type(exc).__name__}"
    except Exception:  # noqa: BLE001
        return [], "Telegram unexpected error on getUpdates"


async def send_message(
    chat_id: str, text: str, *, parse_mode: str = "Markdown"
) -> tuple[bool, str | None, int | None]:
    """Send Telegram message. Returns (ok, error_message, telegram_message_id)."""
    token = get_bot_token()
    if not token:
        return False, "TELEGRAM_BOT_TOKEN is not configured on the server", None

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    last_error: str | None = None

    for attempt in range(MAX_RETRIES):
        try:
            resp = await _get_client().post(url, json=payload)
            ctype = resp.headers.get("content-type", "")
            body = resp.json() if ctype.startswith("application/json") else {}

            if resp.status_code == 200 and body.get("ok"):
                msg_id = (body.get("result") or {}).get("message_id")
                return True, None, msg_id if isinstance(msg_id, int) else None

            # Handle 429 retry-after
            if resp.status_code == 429:
                retry_after = body.get("parameters", {}).get("retry_after")
                if isinstance(retry_after, int) and retry_after > 0:
                    await asyncio.sleep(min(retry_after, 10))
                    continue
                last_error = (
                    f"Telegram 429: {body.get('description', resp.text[:200])}"
                )
            else:
                last_error = body.get("description") or (
                    f"Telegram {resp.status_code}: {resp.text[:300]}"
                )

        except httpx.TimeoutException:
            last_error = "Telegram timeout after 10s"
        except httpx.HTTPError as exc:
            last_error = f"Telegram network error: {type(exc).__name__}: {exc}"
        except Exception as exc:  # noqa: BLE001
            last_error = f"Telegram unexpected: {type(exc).__name__}"

        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(BACKOFF_SECONDS[attempt])

    return False, last_error, None


def build_open_message(monitor_name: str, monitor_url: str, incident_id: str) -> str:
    return (
        f"🔴 *DOWN* — {monitor_name}\n"
        f"{monitor_url}\n\n"
        f"Incident `{incident_id[:8]}` is *OPEN* — 2 consecutive failures.\n"
        f"Reply: check PulseTrack dashboard."
    )


def build_recovery_message(monitor_name: str, monitor_url: str, downtime_min: int) -> str:
    return (
        f"🟢 *RECOVERED* — {monitor_name}\n"
        f"{monitor_url}\n\n"
        f"Back up after {downtime_min} min. Checks are UP again."
    )


def build_escalation_message(monitor_name: str, monitor_url: str, incident_id: str) -> str:
    return (
        f"⚠️ *STILL DOWN* — {monitor_name}\n"
        f"{monitor_url}\n\n"
        f"Incident `{incident_id[:8]}` open for 10 min, *not acknowledged*.\n"
        f"Owner action needed — escalated."
    )


def build_test_message(monitor_name: str | None = None) -> str:
    if monitor_name:
        return f"✅ PulseTrack test OK — *{monitor_name}* — Telegram alerts are working."
    return "✅ PulseTrack test OK — Telegram alerts are working."


def build_heartbeat_down_message(name: str, silent_min: int) -> str:
    return (
        f"💔 *CRON DEAD* — {name}\n\n"
        f"No ping for {silent_min} min. Your scheduled job may have stopped.\n"
        f"Check the job runner."
    )


def build_heartbeat_recovery_message(name: str) -> str:
    return f"💚 *CRON ALIVE* — {name}\n\nPing received again. Job is running."


def build_connected_message(team_name: str | None = None) -> str:
    if team_name:
        return (
            f"✅ *PulseTrack connected* — {team_name}\n\n"
            f"You will get DOWN / RECOVERED alerts here.\n"
            f"No need to copy any chat ID."
        )
    return (
        "✅ *PulseTrack connected*\n\n"
        "You will get DOWN / RECOVERED alerts here.\n"
        "No need to copy any chat ID."
    )
