"""Status shown to admins for each employee of an organization.

Only members go through onboarding and clinical assessments, so the
assessment-driven statuses apply to them alone. Anyone else is reported as
inactive.
"""

from collections.abc import Collection

from app.domain.value_objects.org_role import OrgRole

INACTIVE = "inactive"
ONBOARDING = "onboarding"
UP_TO_DATE = "up_to_date"
PENDING_ASSESSMENTS = "pending_assessments"


def determine_employee_status(
    roles: Collection[OrgRole], onboarded: bool, completed_all_forms: bool
) -> str:
    if not roles or OrgRole.MEMBER not in roles:
        return INACTIVE
    if not onboarded:
        return ONBOARDING
    if completed_all_forms:
        return UP_TO_DATE
    return PENDING_ASSESSMENTS
