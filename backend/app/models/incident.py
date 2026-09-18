import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class IncidentStatus:
    """Plain string constants instead of an enum: stored values must stay
    stable across releases and these are compared as raw strings everywhere."""

    OPEN = "OPEN"
    ACK = "ACK"
    RESOLVED = "RESOLVED"


class Incident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One outage. Created automatically by flap logic (2 consecutive DOWN checks),
    resolved automatically (2 consecutive UP) or manually (Phase 4+ endpoints)."""

    __tablename__ = "incidents"
    __table_args__ = (
        # Hot query: "is there an OPEN incident for this monitor?" on every check.
        Index("ix_incidents_monitor_id_status", "monitor_id", "status"),
        Index("ix_incidents_team_id_started_at", "team_id", "started_at"),
        CheckConstraint(
            "status IN ('OPEN', 'ACK', 'RESOLVED')", name="valid_incident_status"
        ),
    )

    monitor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(10), default=IncidentStatus.OPEN, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ack_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    downtime_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Escalation tracking for Phase 4: when the OPEN alert was escalated (NULL = not yet).
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Filled by the AI analyst in Phase 6; column exists from day one.
    ai_summary: Mapped[str | None] = mapped_column(String, nullable=True)
