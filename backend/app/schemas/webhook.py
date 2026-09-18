import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WebhookIn(BaseModel):
    url: str = Field(min_length=10, max_length=2000)
    secret: str | None = Field(default=None, max_length=128)


class WebhookOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    team_id: uuid.UUID
    url: str
    is_active: bool
    created_at: datetime


class WebhookCreatedOut(WebhookOut):
    # Shown ONCE when auto-generated (we must store it to sign, so unlike API
    # keys this secret lives in our DB — treat it like a password).
    secret: str


class WebhookTestOut(BaseModel):
    ok: bool
    status_code: int | None = None
    error: str | None = None
