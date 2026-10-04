class DomainError(Exception):
    pass


class InviteError(DomainError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class InviteNotFoundError(InviteError):
    def __init__(self):
        super().__init__("invalid_invite")


class InviteExhaustedError(InviteError):
    def __init__(self):
        super().__init__("invite_used")


class InviteExpiredError(InviteError):
    def __init__(self):
        super().__init__("invite_expired")


class InviteEmailMismatchError(InviteError):
    def __init__(self):
        super().__init__("email_mismatch")


class OrganizationSlugAlreadyExists(DomainError):
    pass


class DepartmentSlugAlreadyExists(DomainError):
    pass


class DepartmentNotFoundError(DomainError):
    pass


class DepartmentInUseError(DomainError):
    pass


class DepartmentRequiredError(InviteError):
    def __init__(self):
        super().__init__("department_required")


class InviteDepartmentNotFoundError(InviteError):
    def __init__(self):
        super().__init__("department_not_found")


class DepartmentNotAllowedError(InviteError):
    def __init__(self):
        super().__init__("department_not_allowed_for_admin")


class OrganizationNotFoundError(DomainError):
    pass


class NotOrganizationAdminError(DomainError):
    pass


class UserNotFoundError(DomainError):
    pass


class MembershipNotFoundError(DomainError):
    pass


class InsufficientRolePermissionError(DomainError):
    pass


class CannotRemoveLastSuperadminError(DomainError):
    pass


class CannotRemoveOwnSuperadminError(DomainError):
    """A superadmin cannot remove their own superadmin role or deactivate themselves."""

    pass


class ConsentNotFoundError(DomainError):
    pass


class ConsentAlreadyRevokedError(DomainError):
    pass


class InvalidConsentTypeError(DomainError):
    pass


class FormTypeRequiredError(DomainError):
    pass


class InvalidFormTypeError(DomainError):
    pass


class CannotRevokeFundamentalConsentError(DomainError):
    pass


class HealthTopicsUnavailableError(DomainError):
    """The scoring catalog that declares health topics could not be loaded."""

    pass
