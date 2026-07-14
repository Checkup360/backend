from app.domain.services.password_policy import get_password_policy_error


class ResetPassword:
    def get_validation_error(self, password: str) -> str | None:
        return get_password_policy_error(password)
