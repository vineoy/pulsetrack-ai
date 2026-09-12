from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TeamPlan, enum_values

if TYPE_CHECKING:
    from app.models.user import User


class Team(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    plan: Mapped[TeamPlan] = mapped_column(
        SAEnum(TeamPlan, native_enum=False, length=10, values_callable=enum_values),
        default=TeamPlan.FREE,
        nullable=False,
    )

    users: Mapped[list["User"]] = relationship(back_populates="team", cascade="all, delete-orphan")
