import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Heartbeat(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reverse monitor: the user's cron pings us. Silence past period+grace = MISSING.

    Separate from monitors (no URL/keyword/latency) — just a secret ping_key,
    a promise (period_min), tolerance (grace_min), and last proof of life.
    """

    __tablename__ = "heartbeats"
    __table_args__ = (
        CheckConstraint("period_min >= 1 AND period_min <= 10080", name="valid_hb_period"),
        CheckConstraint("grace_min >= 0 AND grace_min <= 1440", name="valid_hb_grace"),
        CheckConstraint("status IN ('ALIVE', 'MISSING')", name="valid_hb_status"),
        Index("ix_heartbeats_team_id", "team_id"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Secret cron credential: unguessable, rotated by delete+recreate in v1.
    ping_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    period_min: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    grace_min: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    last_ping_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="ALIVE", nullable=False)
