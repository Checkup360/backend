from app.domain import exceptions
from app.domain.value_objects import OrgRole


def test_org_role_values():
    assert OrgRole.ADMIN == "admin"
    assert OrgRole.MEMBER == "member"
    assert OrgRole("admin") == OrgRole.ADMIN
    assert OrgRole("member") == OrgRole.MEMBER


def test_invite_error_codes():
    assert exceptions.InviteNotFoundError().code == "invalid_invite"
    assert exceptions.InviteExhaustedError().code == "invite_used"
    assert exceptions.InviteExpiredError().code == "invite_expired"
    assert exceptions.InviteEmailMismatchError().code == "email_mismatch"
    assert exceptions.DepartmentRequiredError().code == "department_required"
    assert exceptions.InviteDepartmentNotFoundError().code == "department_not_found"
    assert (
        exceptions.DepartmentNotAllowedError().code
        == "department_not_allowed_for_admin"
    )


def test_domain_exceptions_inherit_from_domain_error():
    assert isinstance(
        exceptions.OrganizationSlugAlreadyExists(), exceptions.DomainError
    )
    assert isinstance(exceptions.DepartmentSlugAlreadyExists(), exceptions.DomainError)
    assert isinstance(exceptions.DepartmentNotFoundError(), exceptions.DomainError)
    assert isinstance(exceptions.DepartmentInUseError(), exceptions.DomainError)
    assert isinstance(exceptions.OrganizationNotFoundError(), exceptions.DomainError)
    assert isinstance(exceptions.NotOrganizationAdminError(), exceptions.DomainError)
    assert isinstance(exceptions.UserNotFoundError(), exceptions.DomainError)
