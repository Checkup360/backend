from app.domain.services.password_policy import get_password_policy_error


def test_get_password_policy_error_too_short():
    err = get_password_policy_error("Short1")
    assert err == "Password must contain at least 8 characters."


def test_get_password_policy_error_no_uppercase():
    err = get_password_policy_error("lowercase1")
    assert err == "Password must contain an uppercase letter."


def test_get_password_policy_error_no_lowercase():
    err = get_password_policy_error("UPPERCASE1")
    assert err == "Password must contain a lowercase letter."


def test_get_password_policy_error_no_digit():
    err = get_password_policy_error("NoNumbers")
    assert err == "Password must contain a number."


def test_get_password_policy_error_valid():
    assert get_password_policy_error("ValidPassword1") is None
