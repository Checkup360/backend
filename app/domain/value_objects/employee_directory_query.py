import enum
import uuid
from dataclasses import dataclass, field

from app.domain.value_objects.membership_state import MembershipState
from app.domain.value_objects.org_role import OrgRole
from app.domain.value_objects.sorting import SortDirection


class ScoreFilter(str, enum.Enum):
    SCORED = "scored"
    UNSCORED = "unscored"


class EmployeeSortField(str, enum.Enum):
    NAME = "name"
    ROLES = "roles"
    DEPARTMENT = "department"
    SCORE = "score"
    STATUS = "status"
    LAST_ASSESSMENT = "last_assessment"


@dataclass(frozen=True)
class EmployeeDirectoryQuery:
    """Filters and page requested over the employees of an organization.

    ``required_form_fields`` maps each form the organization requires to the
    health data fields that prove it was filled in; it lets the persistence
    layer derive the assessment status without loading each employee.
    A ``page`` of ``None`` returns every matching employee.
    """

    roles: list[OrgRole] | None = None
    state: MembershipState = MembershipState.ALL
    department_id: uuid.UUID | None = None
    status: str | None = None
    score_filter: ScoreFilter | None = None
    search: str | None = None
    sort_by: EmployeeSortField | None = None
    sort_direction: SortDirection = SortDirection.ASC
    required_form_fields: dict[str, list[str]] = field(default_factory=dict)
    page: int | None = None
    page_size: int = 10
