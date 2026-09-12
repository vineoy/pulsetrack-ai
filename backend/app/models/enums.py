import enum


class UserRole(enum.StrEnum):
    OWNER = "owner"
    MEMBER = "member"
    VIEWER = "viewer"


class TeamPlan(enum.StrEnum):
    FREE = "free"
    PRO = "pro"


def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """values_callable for SAEnum: store 'owner' not 'OWNER' in the database."""
    return [member.value for member in enum_cls]
