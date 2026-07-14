MINIMUM_PASSWORD_LENGTH = 8


def get_password_policy_error(password: str) -> str | None:
    if len(password) < MINIMUM_PASSWORD_LENGTH:
        return f"Password must contain at least {MINIMUM_PASSWORD_LENGTH} characters."
    if not any(character.isupper() for character in password):
        return "Password must contain an uppercase letter."
    if not any(character.islower() for character in password):
        return "Password must contain a lowercase letter."
    if not any(character.isdigit() for character in password):
        return "Password must contain a number."
    return None
