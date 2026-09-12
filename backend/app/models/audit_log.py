import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """Immutable 'who did what, when' trail. Written everywhere, never updated.

    team_id/user_id are SET NULL on delete: the log outlives the rows it points at.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_team_id_created_at", "team_id", "created_at"),)

    team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
