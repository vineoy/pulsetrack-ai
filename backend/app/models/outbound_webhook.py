import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OutboundWebhook(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User URL we POST signed incident JSON to (Phase 7).

    Secret is stored plain (we need it to sign every delivery — unlike API
    keys, hashing is impossible here). Treat it like a password: shown once,
    auto-generated when blank.
    """

    __tablename__ = "outbound_webhooks"
    __table_args__ = (Index("ix_outbound_webhooks_team_id", "team_id"),)

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    secret: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
