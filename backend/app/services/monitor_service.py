import uuid
from datetime import UTC, datetime

from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.monitor import Monitor
from app.models.user import User
from app.repositories import audit_repository, check_repository, monitor_repository
from app.schemas.monitor import (
    FREE_PLAN_MONITOR_LIMIT,
    CheckPage,
    MonitorIn,
    MonitorOut,
    MonitorUpdateIn,
    StatsOut,
)

PLAN_LIMITS = {"free": FREE_PLAN_MONITOR_LIMIT}


async def _owned_monitor(db: AsyncSession, user: User, monitor_id: uuid.UUID) -> Monitor:
    """Tenancy guard: 404 (not 403) when the monitor belongs to another team,
    so we never leak the existence of other teams' resources."""
    monitor = await monitor_repository.get_by_id(db, monitor_id)
    if monitor is None or monitor.team_id != user.team_id:
        raise AppError(http_status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Monitor not found")
    return monitor


async def create_monitor(db: AsyncSession, user: User, data: MonitorIn, ip: str | None) -> Monitor:
    plan = user.team.plan.value if user.team else "free"
    limit = PLAN_LIMITS.get(plan)
    if limit is not None:
        count = await monitor_repository.count_for_team(db, user.team_id)
        if count >= limit:
            raise AppError(
                http_status.HTTP_403_FORBIDDEN,
                "PLAN_LIMIT_REACHED",
                f"The {plan} plan allows {limit} monitors. Upgrade or delete one to add more.",
            )

    monitor = await monitor_repository.create(
        db,
        team_id=user.team_id,
        name=data.name,
        url=str(data.url),
        interval_min=data.interval_min,
        keyword=data.keyword,
        ssl_check=data.ssl_check,
        # Phase 3's scheduler will pick it up immediately when it exists.
        next_check_at=datetime.now(UTC),
    )
    await audit_repository.log(
        db,
        action="monitor.created",
        team_id=user.team_id,
        user_id=user.id,
        target_type="monitor",
        target_id=str(monitor.id),
        detail={"name": monitor.name, "url": monitor.url, "interval_min": monitor.interval_min},
        ip=ip,
    )
    await db.commit()
    return monitor


async def list_monitors(db: AsyncSession, user: User) -> list[dict[str, object]]:
    monitors = await monitor_repository.list_for_team(db, user.team_id)
    latest = await check_repository.latest_per_monitor(db, [m.id for m in monitors])
    rows: list[dict[str, object]] = []
    for monitor in monitors:
        last = latest.get(monitor.id)
        if monitor.is_paused:
            current_status = "PAUSED"
        elif last is None:
            current_status = "PENDING"
        else:
            current_status = last.status
        rows.append(
            {
                **MonitorOut.model_validate(monitor).model_dump(),
                "current_status": current_status,
                "last_latency_ms": last.latency_ms if last else None,
                "last_checked_at": last.checked_at if last else None,
            }
        )
    return rows


async def get_monitor_detail(
    db: AsyncSession, user: User, monitor_id: uuid.UUID
) -> dict[str, object]:
    monitor = await _owned_monitor(db, user, monitor_id)
    checks = await check_repository.recent_for_monitor(db, monitor.id, limit=20)
    stats_row = await monitor_repository.stats(db, monitor.id, days=30)
    total = int(stats_row["total"])
    up = int(stats_row["up"])
    return {
        "monitor": monitor,
        "uptime_pct_30d": round(up / total * 100, 2) if total else None,
        "last_20_checks": checks,
    }


async def update_monitor(
    db: AsyncSession, user: User, monitor_id: uuid.UUID, data: MonitorUpdateIn, ip: str | None
) -> Monitor:
    monitor = await _owned_monitor(db, user, monitor_id)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in changes.items():
        setattr(monitor, field, str(value) if field == "url" and value else value)
    # Recheck on the new settings right away when the scheduler exists.
    if "interval_min" in changes or "url" in changes:
        monitor.next_check_at = datetime.now(UTC)
    await audit_repository.log(
        db,
        action="monitor.updated",
        team_id=user.team_id,
        user_id=user.id,
        target_type="monitor",
        target_id=str(monitor.id),
        detail=changes,
        ip=ip,
    )
    await db.commit()
    await db.refresh(monitor)
    return monitor


async def delete_monitor(
    db: AsyncSession, user: User, monitor_id: uuid.UUID, ip: str | None
) -> None:
    monitor = await _owned_monitor(db, user, monitor_id)
    await audit_repository.log(
        db,
        action="monitor.deleted",
        team_id=user.team_id,
        user_id=user.id,
        target_type="monitor",
        target_id=str(monitor.id),
        detail={"name": monitor.name, "url": monitor.url},
        ip=ip,
    )
    await db.delete(monitor)
    await db.commit()


async def set_paused(
    db: AsyncSession, user: User, monitor_id: uuid.UUID, paused: bool, ip: str | None
) -> Monitor:
    monitor = await _owned_monitor(db, user, monitor_id)
    monitor.is_paused = paused
    if not paused:
        monitor.next_check_at = datetime.now(UTC)
    await audit_repository.log(
        db,
        action="monitor.paused" if paused else "monitor.resumed",
        team_id=user.team_id,
        user_id=user.id,
        target_type="monitor",
        target_id=str(monitor.id),
        ip=ip,
    )
    await db.commit()
    await db.refresh(monitor)
    return monitor


async def get_checks_page(
    db: AsyncSession,
    user: User,
    monitor_id: uuid.UUID,
    *,
    page: int,
    limit: int,
    time_from: datetime | None,
    time_to: datetime | None,
) -> CheckPage:
    await _owned_monitor(db, user, monitor_id)
    checks, total = await check_repository.page_for_monitor(
        db, monitor_id, page=page, limit=limit, time_from=time_from, time_to=time_to
    )
    return CheckPage(
        items=checks,  # type: ignore[arg-type]
        total=total,
        page=page,
        limit=limit,
    )


async def get_stats(db: AsyncSession, user: User, monitor_id: uuid.UUID, days: int) -> StatsOut:
    await _owned_monitor(db, user, monitor_id)
    row = await monitor_repository.stats(db, monitor_id, days=days)
    total = int(row["total"])
    up = int(row["up"])
    return StatsOut(
        monitor_id=monitor_id,
        days=days,
        total_checks=total,
        up_checks=up,
        down_checks=int(row["down"]),
        uptime_pct=round(up / total * 100, 2) if total else 0.0,
        avg_latency_ms=(
            round(float(row["avg_latency"]), 1) if row["avg_latency"] is not None else None
        ),
        p50_latency_ms=round(float(row["p50"]), 1) if row["p50"] is not None else None,
        p95_latency_ms=round(float(row["p95"]), 1) if row["p95"] is not None else None,
        last_checked_at=row["last_checked_at"],  # type: ignore[arg-type]
    )
