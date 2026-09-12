import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log(
    db: AsyncSession,
    *,
    action: str,
    team_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict[str, Any] | None = None,
    ip: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        team_id=team_id,
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        ip=ip,
    )
    db.add(entry)
    await db.flush()
    return entry
