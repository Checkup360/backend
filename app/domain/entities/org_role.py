import enum


class OrgRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
