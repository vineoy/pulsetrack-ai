import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.monitor import Monitor


class Check(Base, UUIDPrimaryKeyMixin):
    """One probe result. Append-only: rows are written by workers, never updated.

    This becomes the biggest table in the system (14,400 rows/day at 1-min checks),
    so it gets a composite index for time-range scans + a BRIN index on checked_at
    (tiny index, perfect for append-only time data).
    """

    __tablename__ = "checks"
    __table_args__ = (
        Index("ix_checks_monitor_id_checked_at", "monitor_id", "checked_at"),
        Index("ix_checks_brin_checked_at", "checked_at", postgresql_using="brin"),
    )

    monitor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False
    )
    # "UP" / "DOWN" (kept as plain string for now; worker logic arrives in Phase 3)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status_code: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    monitor: Mapped["Monitor"] = relationship(back_populates="checks")
