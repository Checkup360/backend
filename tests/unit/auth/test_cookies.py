from unittest.mock import MagicMock

from app.infrastructure.authentication.machinery.cookies import (
    apply_pending_invite_cookie,
    clear_pending_invite_cookie,
)


def test_apply_pending_invite_cookie():
    """Test that pending invite cookie is set correctly."""
    response = MagicMock()
    token = "test-invite-token-123"

    apply_pending_invite_cookie(response, token)

    response.set_cookie.assert_called_once()


def test_clear_pending_invite_cookie():
    """Test that pending invite cookie is cleared correctly."""
    response = MagicMock()

    clear_pending_invite_cookie(response)

    response.delete_cookie.assert_called_once()


def test_set_refresh_cookie_default_path():
    from app.infrastructure.authentication.machinery.backend import cookie_transport

    response = MagicMock()
    cookie_transport._set_refresh_cookie(response, "dummy-token")

    response.set_cookie.assert_called_once()
    _, kwargs = response.set_cookie.call_args
    assert kwargs["path"] == "/auth"


def test_set_refresh_cookie_with_forwarded_prefix():
    from app.infrastructure.authentication.machinery.backend import cookie_transport

    response = MagicMock()
    request = MagicMock()
    request.headers.get.side_effect = lambda k, default="": (
        "/api" if k == "x-forwarded-prefix" else default
    )

    cookie_transport._set_refresh_cookie(response, "dummy-token", request=request)

    response.set_cookie.assert_called_once()
    _, kwargs = response.set_cookie.call_args
    assert kwargs["path"] == "/api/auth"


def test_set_logout_cookie_clears_multiple_paths():
    from app.infrastructure.authentication.machinery.backend import cookie_transport

    response = MagicMock()
    cookie_transport._set_logout_cookie(response)

    paths = [call[1]["path"] for call in response.set_cookie.call_args_list]
    assert "/auth" in paths
    assert "/api/auth" in paths
