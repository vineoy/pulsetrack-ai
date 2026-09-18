"""check_job: the probe that actually pings websites.

Design rules (roadmap section 08):
- Redis distributed lock per monitor -> two workers can never double-check.
- httpx GET, 10s timeout, follows redirects, custom User-Agent.
- Any exception (timeout, DNS, TLS) becomes a DOWN check - never crashes the worker.
- UP  = 200 <= status_code < 400 AND keyword present (when keyword is set).
- DOWN = everything else: timeout, connection error, 4xx, 5xx, missing keyword.
- After saving: next_check_at = now + interval, then flap logic may open/resolve incidents.
"""

import ssl
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select

from app.core.db import async_session_factory
from app.core.redis import redis_client
from app.models.monitor import Monitor
from app.repositories import check_repository
from app.services.incident_service import apply_flap_logic

LOCK_TTL_SECONDS = 60
HTTP_TIMEOUT_SECONDS = 10.0

# Injectable for tests: swapped for httpx.MockTransport-backed clients.
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(HTTP_TIMEOUT_SECONDS),
            follow_redirects=True,
            headers={"User-Agent": "PulseTrackAI/0.1 (+uptime-monitor)"},
        )
    return _client


def set_client_for_testing(client: httpx.AsyncClient | None) -> None:
    global _client
    _client = client


@dataclass
class ProbeResult:
    status: str  # "UP" | "DOWN"
    latency_ms: int | None
    status_code: int | None
    error: str | None


def decide_outcome(status_code: int | None, body: str, keyword: str | None) -> bool:
    """Pure UP/DOWN decision - unit-testable without any network."""
    if status_code is None:
        return False
    if not (200 <= status_code < 400):
        return False
    if keyword and keyword not in body:
        return False
    return True


async def probe(monitor: Monitor) -> ProbeResult:
    """One HTTP probe. Exceptions become DOWN results, never exceptions."""
    started = datetime.now(UTC)
    try:
        response = await _get_client().get(monitor.url)
        latency_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
        up = decide_outcome(response.status_code, response.text or "", monitor.keyword)
        return ProbeResult(
            status="UP" if up else "DOWN",
            latency_ms=latency_ms,
            status_code=response.status_code,
            error=(
                None
                if up
                else _describe_failure(response.status_code, monitor.keyword, response.text or "")
            ),
        )
    except httpx.TimeoutException:
        return ProbeResult("DOWN", None, None, f"timeout after {HTTP_TIMEOUT_SECONDS:.0f}s")
    except ssl.SSLCertVerificationError as exc:
        msg = exc.verify_message or "invalid certificate"
        return ProbeResult("DOWN", None, None, f"SSL verification failed: {msg}")
    except httpx.HTTPError as exc:
        return ProbeResult("DOWN", None, None, f"http error: {type(exc).__name__}")
    except Exception as exc:  # noqa: BLE001 - a probe must never crash the worker
        return ProbeResult("DOWN", None, None, f"unexpected: {type(exc).__name__}")


def _describe_failure(status_code: int, keyword: str | None, body: str) -> str:
    if keyword and keyword not in body:
        return f"keyword '{keyword}' not found in response"
    if status_code >= 500:
        return f"server error {status_code}"
    return f"http status {status_code}"


async def check_job(ctx: dict, monitor_id: str) -> str:
    """ARQ job: probe one monitor, persist the check, run flap logic."""
    mid = uuid.UUID(monitor_id)
    lock_key = f"lock:monitor:{mid}"

    # Distributed lock: with 2+ workers, whoever loses skips (the monitor is
    # already being checked by the other worker this tick).
    got_lock = await redis_client.set(lock_key, "1", nx=True, ex=LOCK_TTL_SECONDS)
    if not got_lock:
        return "skipped:locked"

    try:
        async with async_session_factory() as db:
            monitor = await db.get(Monitor, mid)
            if monitor is None or monitor.is_paused:
                return "skipped:monitor"

            result = await probe(monitor)
            checked_at = datetime.now(UTC)
            await check_repository.create(
                db,
                monitor_id=mid,
                status=result.status,
                latency_ms=result.latency_ms,
                status_code=result.status_code,
                error=result.error,
                checked_at=checked_at,
            )
            monitor.next_check_at = datetime.now(UTC) + timedelta(
                minutes=monitor.interval_min
            )

            incident = await apply_flap_logic(db, monitor)
            # Remember whether this transition was OPEN or RESOLVED for alert enqueue
            incident_kind: str | None = None
            incident_id_for_alert: str | None = None
            if incident is not None:
                if incident.status == "OPEN":
                    incident_kind = "open"
                    incident_id_for_alert = str(incident.id)
                elif incident.status == "RESOLVED":
                    incident_kind = "recovery"
                    incident_id_for_alert = str(incident.id)
            await db.commit()

            outcome = f"{result.status} {result.status_code or '-'} {result.latency_ms or '-'}ms"
            if incident is not None:
                outcome += f" incident:{incident.status}"

            # Enqueue Telegram alert + webhook delivery outside the DB transaction
            # but before releasing lock, so we never miss a notification.
            # ctx["redis"] is the ARQ pool.
            if incident_kind and incident_id_for_alert:
                try:
                    await ctx["redis"].enqueue_job(
                        "telegram_alert_job", incident_id_for_alert, incident_kind
                    )
                    outcome += f" alert:{incident_kind} queued"
                except Exception:
                    # Queue full or Redis blip — sweep cron will catch OPEN escalation,
                    # but for now we don't fail the check itself.
                    pass
                try:
                    await ctx["redis"].enqueue_job(
                        "webhook_delivery_job", incident_id_for_alert, incident_kind
                    )
                    outcome += " webhook:queued"
                except Exception:
                    pass

            # Live fan-out (Phase 5): publish AFTER commit so subscribers never see
            # a check that gets rolled back. Best-effort — never fails the probe.
            # Cache invalidation for the public status page happens here too.
            try:
                from app.services import live_service

                incident_label = None
                if incident is not None:
                    incident_label = incident.status  # OPEN | RESOLVED
                await live_service.publish_check(
                    redis_client,
                    live_service.build_check_event(
                        team_id=monitor.team_id,
                        monitor_id=mid,
                        status=result.status,
                        latency_ms=result.latency_ms,
                        status_code=result.status_code,
                        checked_at=checked_at,
                        incident=incident_label,
                    ),
                )
                if incident is not None or result.status == "DOWN":
                    try:
                        from app.models.team import Team

                        team = await db.get(Team, monitor.team_id)
                        await live_service.invalidate_public_cache(
                            redis_client, team.slug if team else None
                        )
                    except Exception:  # noqa: BLE001
                        pass
            except Exception:  # noqa: BLE001
                pass
            return outcome
    finally:
        await redis_client.delete(lock_key)


async def enqueue_due_monitors(ctx: dict) -> int:
    """Scheduler body (runs every 30s): push due monitors onto the queue."""
    now = datetime.now(UTC)
    async with async_session_factory() as db:
        result = await db.execute(
            select(Monitor.id)
            .where(Monitor.is_paused.is_(False), Monitor.next_check_at <= now)
            .limit(500)
        )
        due = [str(row) for row in result.scalars().all()]

    for monitor_id in due:
        await ctx["redis"].enqueue_job("check_job", monitor_id)
    return len(due)
