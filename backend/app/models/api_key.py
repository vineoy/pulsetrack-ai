import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ApiKey(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Machine credential for scripts/CI (Phase 7).

    The raw key (`pk_live_...`) is shown ONCE at creation and never stored —
    only prefix (for lookup) + SHA256 hash (one-way fingerprint).
    Auth resolves the key to its creator user, so keys inherit the creator's
    role and die with deactivation/deletion (CASCADE).
    """

    __tablename__ = "api_keys"
    __table_args__ = (Index("ix_api_keys_team_id", "team_id"),)

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
