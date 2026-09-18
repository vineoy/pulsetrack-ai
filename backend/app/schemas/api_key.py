import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ApiKeyOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    team_id: uuid.UUID
    name: str
    prefix: str
    created_at: datetime


class ApiKeyCreatedOut(ApiKeyOut):
    # Shown ONCE — the raw key is never stored and can never be revealed again.
    key: str
