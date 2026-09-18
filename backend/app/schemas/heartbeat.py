import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class HeartbeatIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    period_min: int = Field(default=5, ge=1, le=10080)
    grace_min: int = Field(default=2, ge=0, le=1440)


class HeartbeatOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    team_id: uuid.UUID
    name: str
    period_min: int
    grace_min: int
    last_ping_at: datetime | None
    status: str
    created_at: datetime


class HeartbeatCreatedOut(HeartbeatOut):
    # Shown ONCE at creation — the cron secret. v1 has no "reveal" endpoint.
    ping_key: str
