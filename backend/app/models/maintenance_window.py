import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MaintenanceWindow(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Mute Telegram alerts for a time range. Checks still run & are saved.

    monitor_id = None → whole team is in maintenance (deploy freeze).
    Otherwise mute only that one monitor.
    """

    __tablename__ = "maintenance_windows"
    __table_args__ = (
        Index("ix_maintenance_team_id_starts", "team_id", "starts_at"),
        Index("ix_maintenance_monitor_id", "monitor_id"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    monitor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("monitors.id", ondelete="CASCADE"), nullable=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
