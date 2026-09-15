import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.check import Check


class Monitor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "monitors"
    __table_args__ = (CheckConstraint("interval_min IN (1, 5, 10, 30)", name="valid_interval"),)

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(10), default="GET", nullable=False)
    # Allowed intervals: 1/5/10/30 minutes (enforced by the CheckConstraint above).
    interval_min: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    keyword: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ssl_check: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_paused: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Scheduler (Phase 3) picks up monitors where next_check_at <= now().
    next_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    checks: Mapped[list["Check"]] = relationship(
        back_populates="monitor", cascade="all, delete-orphan"
    )
