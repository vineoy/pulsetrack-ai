"""CSV exports (Phase 8) — streaming, team-scoped, capped.

Memory stays flat (~2,000 rows) no matter the total: chunks are SELECTed,
formatted, and yielded one at a time. Cap 50,000 rows — pick a smaller date
range beyond that. The csv module quotes commas/newlines in error text.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime

MAX_EXPORT_ROWS = 50_000
CHUNK_SIZE = 2_000


def _chunk_to_csv(rows: list[list[object]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    return buf.getvalue()


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


async def stream_checks_csv(db, monitor_id: uuid.UUID, time_from, time_to):
    from app.repositories import check_repository

    yield _chunk_to_csv([["checked_at", "status", "latency_ms", "status_code", "error"]])
    exported = 0
    while exported < MAX_EXPORT_ROWS:
        # Constant limit keeps offset math exact; the slice enforces the cap.
        checks, _total = await check_repository.page_for_monitor(
            db,
            monitor_id,
            page=exported // CHUNK_SIZE + 1,
            limit=CHUNK_SIZE,
            time_from=time_from,
            time_to=time_to,
        )
        if not checks:
            break
        checks = checks[: MAX_EXPORT_ROWS - exported]
        yield _chunk_to_csv(
            [
                [_iso(c.checked_at), c.status, c.latency_ms, c.status_code, c.error or ""]
                for c in checks
            ]
        )
        exported += len(checks)
        if len(checks) < CHUNK_SIZE:
            break


async def stream_incidents_csv(db, team_id: uuid.UUID, status: str | None):
    from sqlalchemy import select

    from app.models.monitor import Monitor
    from app.repositories import incident_repository

    result = await db.execute(select(Monitor).where(Monitor.team_id == team_id))
    names = {m.id: m.name for m in result.scalars().all()}

    yield _chunk_to_csv(
        [["id", "monitor", "status", "started_at", "resolved_at", "downtime_min"]]
    )
    exported = 0
    while exported < MAX_EXPORT_ROWS:
        incidents = await incident_repository.page_for_team(
            db, team_id, status=status, offset=exported, limit=CHUNK_SIZE
        )
        if not incidents:
            break
        incidents = incidents[: MAX_EXPORT_ROWS - exported]
        yield _chunk_to_csv(
            [
                [
                    str(inc.id),
                    names.get(inc.monitor_id, "Monitor"),
                    inc.status,
                    _iso(inc.started_at),
                    _iso(inc.resolved_at),
                    round((inc.downtime_sec or 0) / 60, 1),
                ]
                for inc in incidents
            ]
        )
        exported += len(incidents)
        if len(incidents) < CHUNK_SIZE:
            break
