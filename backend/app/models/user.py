import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole, enum_values

if TYPE_CHECKING:
    from app.models.team import Team


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, native_enum=False, length=10, values_callable=enum_values),
        default=UserRole.MEMBER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # selectin: team is loaded with one extra SELECT instead of raising the
    # async-forbidden lazy-load error when we touch user.team.
    team: Mapped["Team"] = relationship(back_populates="users", lazy="selectin")
