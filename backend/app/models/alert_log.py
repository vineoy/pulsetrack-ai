import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AlertLog(Base, UUIDPrimaryKeyMixin):
    """Receipt for every alert — success, failed, or skipped (maintenance/no-channel)."""

    __tablename__ = "alert_logs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('sent','failed','skipped')", name="valid_alert_status"
        ),
        CheckConstraint(
            "kind IN ('open','recovery','escalation','test')", name="valid_alert_kind"
        ),
        Index("ix_alert_logs_incident_id", "incident_id"),
        Index("ix_alert_logs_channel_id", "channel_id"),
        Index("ix_alert_logs_team_id_sent_at", "team_id", "sent_at"),
    )

    # Not UUIDPrimaryKeyMixin timestamp — sent_at is the domain clock; created_at mirrors it.
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True
    )
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("notification_channels.id", ondelete="SET NULL"), nullable=True
    )
    monitor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("monitors.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(12), nullable=False)  # open/recovery/escalation/test
    status: Mapped[str] = mapped_column(String(10), nullable=False)  # sent/failed/skipped
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
