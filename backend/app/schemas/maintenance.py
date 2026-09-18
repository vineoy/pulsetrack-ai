import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator


class MaintenanceIn(BaseModel):
    monitor_id: uuid.UUID | None = Field(
        default=None, description="Null = whole team in maintenance"
    )
    starts_at: datetime
    ends_at: datetime
    reason: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def validate_window(self) -> "MaintenanceIn":
        # Ensure timezone-aware and ends after starts
        if self.starts_at.tzinfo is None:
            self.starts_at = self.starts_at.replace(tzinfo=UTC)
        if self.ends_at.tzinfo is None:
            self.ends_at = self.ends_at.replace(tzinfo=UTC)
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        # Window must be at least 1 minute, at most 24h
        delta = (self.ends_at - self.starts_at).total_seconds()
        if delta < 60:
            raise ValueError("window must be at least 1 minute")
        if delta > 86400:
            raise ValueError("window must be at most 24 hours")
        return self


class MaintenanceOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    team_id: uuid.UUID
    monitor_id: uuid.UUID | None
    starts_at: datetime
    ends_at: datetime
    reason: str | None
    created_at: datetime
