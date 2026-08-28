import enum


class OrgRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
    CONTENT_MANAGER = "content_manager"
