from datetime import datetime

from pydantic import BaseModel


class PublicMonitorOut(BaseModel):
    id: str
    name: str
    current_status: str  # UP | DOWN | PAUSED | PENDING
    last_latency_ms: int | None
    last_checked_at: datetime | None


class PublicStatusOut(BaseModel):
    team_name: str
    slug: str
    overall: str  # operational | degraded | outage
    open_incidents: int
    monitors: list[PublicMonitorOut]


class PublicIncidentOut(BaseModel):
    id: str
    monitor_name: str
    status: str
    started_at: datetime
    resolved_at: datetime | None
    downtime_sec: int | None
