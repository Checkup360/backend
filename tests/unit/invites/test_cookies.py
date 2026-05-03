from unittest.mock import MagicMock

from app.invites.cookies import apply_pending_invite_cookie, clear_pending_invite_cookie


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
