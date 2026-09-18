import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TelegramChannelIn(BaseModel):
    telegram_chat_id: str = Field(
        min_length=3,
        max_length=64,
        description="Telegram chat/channel ID, e.g. 123456789 or -1001234567890",
    )
    label: str | None = Field(default=None, max_length=100)


class TelegramChannelOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    team_id: uuid.UUID
    type: str
    telegram_chat_id: str
    label: str | None
    is_active: bool
    created_at: datetime


class TelegramTestOut(BaseModel):
    ok: bool
    message: str


class TelegramConnectIn(BaseModel):
    label: str | None = Field(default=None, max_length=100)


class TelegramConnectOut(BaseModel):
    token: str
    deep_link: str | None
    expires_in_sec: int


class TelegramConnectStatusOut(BaseModel):
    status: str  # pending | connected | expired
    channel: TelegramChannelOut | None = None
