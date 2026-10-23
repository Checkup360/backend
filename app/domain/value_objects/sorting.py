import enum


class SortDirection(str, enum.Enum):
    ASC = "asc"
    DESC = "desc"


class OrganizationSortField(str, enum.Enum):
    NAME = "name"
    COLLABORATORS = "collaborators"
    STATUS = "status"


class SysadminSortField(str, enum.Enum):
    NAME = "name"
    STATUS = "status"


class AuditLogSortField(str, enum.Enum):
    ACTION = "action"
    CREATED_AT = "created_at"
