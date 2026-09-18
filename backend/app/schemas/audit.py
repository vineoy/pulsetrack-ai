import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    team_id: uuid.UUID | None
    user_id: uuid.UUID | None
    action: str
    target_type: str | None
    target_id: str | None
    detail: dict[str, Any] | None
    ip: str | None
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    limit: int
