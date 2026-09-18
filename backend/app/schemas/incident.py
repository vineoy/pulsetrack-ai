import uuid
from datetime import datetime

from pydantic import BaseModel


class IncidentOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    team_id: uuid.UUID
    monitor_id: uuid.UUID
    status: str
    started_at: datetime
    ack_at: datetime | None
    resolved_at: datetime | None
    downtime_sec: int | None
    escalated_at: datetime | None
    created_at: datetime
