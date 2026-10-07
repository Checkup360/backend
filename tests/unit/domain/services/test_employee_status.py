import pytest

from app.domain.services.employee_status import determine_employee_status
from app.domain.value_objects.org_role import OrgRole


def test_user_without_roles_is_inactive():
    assert determine_employee_status([], onboarded=True, completed_all_forms=True) == (
        "inactive"
    )


@pytest.mark.parametrize(
    "roles",
    [
        [OrgRole.SUPERADMIN],
        [OrgRole.ADMIN],
        [OrgRole.CONTENT_MANAGER],
        [OrgRole.ADMIN, OrgRole.CONTENT_MANAGER],
    ],
)
def test_user_with_roles_but_not_member_has_no_status(roles):
    assert (
        determine_employee_status(roles, onboarded=False, completed_all_forms=False)
        is None
    )


def test_member_not_onboarded_is_onboarding():
    assert (
        determine_employee_status(
            [OrgRole.MEMBER], onboarded=False, completed_all_forms=False
        )
        == "onboarding"
    )


def test_onboarded_member_with_all_forms_is_up_to_date():
    assert (
        determine_employee_status(
            [OrgRole.MEMBER, OrgRole.ADMIN], onboarded=True, completed_all_forms=True
        )
        == "up_to_date"
    )


def test_onboarded_member_missing_forms_has_pending_assessments():
    assert (
        determine_employee_status(
            [OrgRole.MEMBER], onboarded=True, completed_all_forms=False
        )
        == "pending_assessments"
    )
