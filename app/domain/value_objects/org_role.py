import enum


class OrgRole(str, enum.Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    MEMBER = "member"
    CONTENT_MANAGER = "content_manager"
