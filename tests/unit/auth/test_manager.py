import pytest
from fastapi import HTTPException


class TestInviteTokenFromRequest:
    def test_token_from_override(self, user_manager, request_mock):
        request_mock.state.invite_token_override = "override-token"

        token = user_manager._invite_token_from_request(request_mock)

        assert token == "override-token"

    def test_token_from_cookie(self, user_manager, request_mock):
        request_mock.cookies = {"pending_invite": "cookie-token"}

        token = user_manager._invite_token_from_request(request_mock)

        assert token == "cookie-token"

    def test_no_token_fails(self, user_manager, request_mock):
        with pytest.raises(HTTPException) as exc_info:
            user_manager._invite_token_from_request(request_mock)

        assert exc_info.value.status_code == 303

    def test_no_request_fails(self, user_manager):
        with pytest.raises(HTTPException):
            user_manager._invite_token_from_request(None)


class TestInviteFail:
    def test_invite_fail_redirect_by_default(self, user_manager, request_mock):
        with pytest.raises(HTTPException) as exc_info:
            user_manager._invite_fail(request_mock, "invite_expired")

        assert exc_info.value.status_code == 303
        assert "invite_expired" in exc_info.value.headers.get("Location", "")

    def test_invite_fail_json_mode(self, user_manager, request_mock):
        request_mock.state.invite_validation_error_as_json = True

        with pytest.raises(HTTPException) as exc_info:
            user_manager._invite_fail(request_mock, "invite_used")

        assert exc_info.value.status_code == 400
        assert "code" in exc_info.value.detail or isinstance(
            exc_info.value.detail, dict
        )

    def test_invite_fail_sets_clear_cookie_flag(self, user_manager, request_mock):
        try:
            user_manager._invite_fail(request_mock, "no_invite")
        except HTTPException:
            pass

        assert request_mock.state.clear_pending_invite_cookie is True

    def test_invite_fail_no_request(self, user_manager):
        with pytest.raises(HTTPException):
            user_manager._invite_fail(None, "no_invite")
