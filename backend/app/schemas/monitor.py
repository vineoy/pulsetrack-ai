import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

ALLOWED_INTERVALS = (1, 5, 10, 30)
FREE_PLAN_MONITOR_LIMIT = 10


class MonitorIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: HttpUrl  # pydantic rejects "not a url" before the DB ever sees it
    interval_min: Literal[1, 5, 10, 30] = 1
    keyword: str | None = Field(default=None, max_length=200)
    ssl_check: bool = False

    @field_validator("keyword")
    @classmethod
    def _strip_keyword(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class MonitorUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: HttpUrl | None = None
    interval_min: Literal[1, 5, 10, 30] | None = None
    keyword: str | None = Field(default=None, max_length=200)
    ssl_check: bool | None = None


class MonitorOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    url: str
    method: str
    interval_min: int
    keyword: str | None
    ssl_check: bool
    is_paused: bool
    next_check_at: datetime | None
    created_at: datetime


class MonitorSummaryOut(MonitorOut):
    """Row in the dashboard list: monitor + its last probe result."""

    current_status: Literal["UP", "DOWN", "PAUSED", "PENDING"] = "PENDING"
    last_latency_ms: int | None = None
    last_checked_at: datetime | None = None


class CheckOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    status: str
    latency_ms: int | None
    status_code: int | None
    error: str | None
    checked_at: datetime


class CheckPage(BaseModel):
    items: list[CheckOut]
    total: int
    page: int
    limit: int


class StatsOut(BaseModel):
    monitor_id: uuid.UUID
    days: int
    total_checks: int
    up_checks: int
    down_checks: int
    uptime_pct: float
    avg_latency_ms: float | None
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    last_checked_at: datetime | None
