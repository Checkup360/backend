import enum
import uuid
from dataclasses import dataclass, field

from app.domain.value_objects.membership_state import MembershipState
from app.domain.value_objects.org_role import OrgRole


class ScoreFilter(str, enum.Enum):
    SCORED = "scored"
    UNSCORED = "unscored"


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
    required_form_fields: dict[str, list[str]] = field(default_factory=dict)
    page: int | None = None
    page_size: int = 10
