import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NotificationChannel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Telegram-only channel. One row per team chat that receives alerts.

    Single-team = single row typical, but schema allows many chats per team
    (e.g. ops channel + dev channel) — future-proof without extra migration.
    """

    __tablename__ = "notification_channels"
    __table_args__ = (
        CheckConstraint("type = 'telegram'", name="type_telegram_only"),
        Index("ix_notification_channels_team_id_type", "team_id", "type"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), default="telegram", nullable=False)
    telegram_chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # Human label: "Ops channel", "My DM", etc.
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
