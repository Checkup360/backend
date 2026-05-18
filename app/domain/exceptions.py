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


class OrganizationNotFoundError(DomainError):
    pass


class NotOrganizationAdminError(DomainError):
    pass
