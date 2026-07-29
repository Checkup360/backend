from unittest.mock import MagicMock

import pytest

from app.application.use_cases.authentication import RequestPasswordReset, ResetPassword


@pytest.mark.asyncio
async def test_request_password_reset_sends_encoded_link():
    email_sender = MagicMock()
    use_case = RequestPasswordReset(email_sender, "https://app.example.com/")

    await use_case.execute("user@example.com", "signed token/value")

    email_sender.send_password_reset_email.assert_called_once_with(
        "user@example.com",
        "https://app.example.com/reset-password?token=signed+token%2Fvalue",
    )


@pytest.mark.asyncio
async def test_request_password_reset_strips_trailing_slash_from_origin():
    email_sender = MagicMock()
    use_case = RequestPasswordReset(email_sender, "https://app.example.com///")

    await use_case.execute("test@example.com", "token123")

    email_sender.send_password_reset_email.assert_called_once_with(
        "test@example.com",
        "https://app.example.com/reset-password?token=token123",
    )


@pytest.mark.parametrize(
    ("password", "expected_error"),
    [
        ("Short1", "at least 8"),
        ("lowercase1", "uppercase"),
        ("UPPERCASE1", "lowercase"),
        ("NoNumbers", "number"),
    ],
)
def test_reset_password_rejects_weak_passwords(password, expected_error):
    error = ResetPassword().get_validation_error(password)
    assert error is not None
    assert expected_error in error


def test_reset_password_accepts_strong_password():
    assert ResetPassword().get_validation_error("StrongPass1") is None
