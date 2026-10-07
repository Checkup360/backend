"""Status shown to admins for each employee of an organization.

Only members go through onboarding and clinical assessments, so the
assessment-driven statuses apply to them alone. A user without any role has
been deactivated. A user with roles but without the member role (e.g. only
admin or content manager) has no employee status.
"""

from collections.abc import Collection

from app.domain.value_objects.org_role import OrgRole

INACTIVE = "inactive"
ONBOARDING = "onboarding"
UP_TO_DATE = "up_to_date"
PENDING_ASSESSMENTS = "pending_assessments"


def determine_employee_status(
    roles: Collection[OrgRole], onboarded: bool, completed_all_forms: bool
) -> str | None:
    if not roles:
        return INACTIVE
    if OrgRole.MEMBER not in roles:
        return None
    if not onboarded:
        return ONBOARDING
    if completed_all_forms:
        return UP_TO_DATE
    return PENDING_ASSESSMENTS
