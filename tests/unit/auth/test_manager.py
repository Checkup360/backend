"""
Unit tests for UserManager and invite logic.
"""

import pytest
from fastapi import HTTPException
import uuid

from app.models.membership import OrgRole


class TestInviteTokenFromRequest:
    """Tests for extracting the invite token from the request."""

    def test_token_from_override(self, user_manager, request_mock):
        """Token prioritario desde override."""
        request_mock.state.invite_token_override = "override-token"

        token = user_manager._invite_token_from_request(request_mock)

        assert token == "override-token"

    def test_token_from_cookie(self, user_manager, request_mock):
        """Token from the pending_invite cookie."""
        request_mock.cookies = {"pending_invite": "cookie-token"}

        token = user_manager._invite_token_from_request(request_mock)

        assert token == "cookie-token"

    def test_override_takes_priority_over_cookie(self, user_manager, request_mock):
        """Override takes priority over the cookie."""
        request_mock.state.invite_token_override = "override-token"
        request_mock.cookies = {"pending_invite": "cookie-token"}

        token = user_manager._invite_token_from_request(request_mock)

        assert token == "override-token"

    def test_no_token_fails(self, user_manager, request_mock):
        """Missing token raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            user_manager._invite_token_from_request(request_mock)

        assert exc_info.value.status_code == 303

    def test_no_request_fails(self, user_manager):
        """Missing request fails."""
        with pytest.raises(HTTPException):
            user_manager._invite_token_from_request(None)


class TestHasInviteToken:
    """Tests for checking whether a token exists without failing."""

    def test_has_invite_token_with_override(self, user_manager, request_mock):
        """Detects a token in the override."""
        request_mock.state.invite_token_override = "token"

        assert user_manager._has_invite_token(request_mock) is True

    def test_has_invite_token_with_cookie(self, user_manager, request_mock):
        """Detects a token in the cookie."""
        request_mock.cookies = {"pending_invite": "token"}

        assert user_manager._has_invite_token(request_mock) is True

    def test_no_invite_token(self, user_manager, request_mock):
        """Returns False when no token exists."""
        assert user_manager._has_invite_token(request_mock) is False

    def test_no_request_returns_false(self, user_manager):
        """Returns False without a request (does not fail)."""
        assert user_manager._has_invite_token(None) is False


class TestInviteFail:
    """Tests for invite error handling."""

    def test_invite_fail_redirect_by_default(self, user_manager, request_mock):
        """Redirects to the frontend with an error by default."""
        with pytest.raises(HTTPException) as exc_info:
            user_manager._invite_fail(request_mock, "invite_expired")

        assert exc_info.value.status_code == 303
        assert "invite_expired" in exc_info.value.headers.get("Location", "")

    def test_invite_fail_json_mode(self, user_manager, request_mock):
        """Returns 400 with detail in JSON mode."""
        request_mock.state.invite_validation_error_as_json = True

        with pytest.raises(HTTPException) as exc_info:
            user_manager._invite_fail(request_mock, "invite_used")

        assert exc_info.value.status_code == 400
        assert isinstance(exc_info.value.detail, dict)

    def test_invite_fail_sets_clear_cookie_flag(self, user_manager, request_mock):
        """Failure sets the flag to clear the cookie."""
        try:
            user_manager._invite_fail(request_mock, "no_invite")
        except HTTPException:
            pass

        assert request_mock.state.clear_pending_invite_cookie is True

    def test_invite_fail_no_request(self, user_manager):
        """Fails without a request without issues."""
        with pytest.raises(HTTPException):
            user_manager._invite_fail(None, "no_invite")


class TestConsumeInviteByID:
    """Tests for invite consumption and role assignment."""

    @pytest.mark.asyncio
    async def test_consume_invite_creates_membership_new_user(
        self,
        user_manager,
        sample_user,
        sample_invite_org,
        invite_repo_mock,
        membership_repo_mock,
        user_repo_mock,
    ):
        """New user: create membership with the invite role."""
        invite_repo_mock.get.return_value = sample_invite_org
        user_repo_mock.get.return_value = sample_user
        membership_repo_mock.get_by_user_and_org.return_value = None

        await user_manager._consume_invite_by_id(sample_invite_org.id, sample_user)

        # Verify the membership was created
        membership_repo_mock.create.assert_called_once()
        args = membership_repo_mock.create.call_args[1]
        assert args["user_id"] == sample_user.id
        assert args["organization_id"] == sample_invite_org.organization_id
        assert args["role"] == OrgRole.MEMBER

        # Verify the invite was consumed
        assert sample_invite_org.uses == 1
        invite_repo_mock.save.assert_called_once_with(sample_invite_org)

    @pytest.mark.asyncio
    async def test_consume_invite_admin_preserves_role(
        self,
        user_manager,
        sample_user,
        sample_invite_org,
        sample_membership,
        invite_repo_mock,
        membership_repo_mock,
        user_repo_mock,
    ):
        """ADMIN user: does NOT downgrade role when consuming a MEMBER invite."""
        # Setup: user is ADMIN in the org
        sample_membership.user_id = sample_user.id
        sample_membership.organization_id = sample_invite_org.organization_id
        sample_membership.role = OrgRole.ADMIN

        # Invite attempts to assign MEMBER
        sample_invite_org.role = OrgRole.MEMBER

        invite_repo_mock.get.return_value = sample_invite_org
        user_repo_mock.get.return_value = sample_user
        membership_repo_mock.get_by_user_and_org.return_value = sample_membership

        await user_manager._consume_invite_by_id(sample_invite_org.id, sample_user)

        # Verify no membership was created
        membership_repo_mock.create.assert_not_called()

        # Verify the role remained ADMIN
        assert sample_membership.role == OrgRole.ADMIN

        # Verify the invite was not consumed
        assert sample_invite_org.uses == 0
        invite_repo_mock.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_consume_invite_sysadmin_sets_superuser(
        self,
        user_manager,
        sample_user,
        sample_invite_sysadmin,
        invite_repo_mock,
        user_repo_mock,
    ):
        """Sysadmin invite sets user.is_superuser = True."""
        invite_repo_mock.get.return_value = sample_invite_sysadmin
        user_repo_mock.get.return_value = sample_user

        await user_manager._consume_invite_by_id(sample_invite_sysadmin.id, sample_user)

        # Verify superuser
        user_repo_mock.update.assert_called_once_with(sample_user.id, is_superuser=True)

        # Verify the invite was consumed
        assert sample_invite_sysadmin.uses == 1
        invite_repo_mock.save.assert_called_once_with(sample_invite_sysadmin)

    @pytest.mark.asyncio
    async def test_consume_invite_default_member_role(
        self,
        user_manager,
        sample_user,
        sample_invite_org,
        invite_repo_mock,
        membership_repo_mock,
        user_repo_mock,
    ):
        """Invite without a role uses MEMBER by default."""
        sample_invite_org.role = None

        invite_repo_mock.get.return_value = sample_invite_org
        user_repo_mock.get.return_value = sample_user
        membership_repo_mock.get_by_user_and_org.return_value = None

        await user_manager._consume_invite_by_id(sample_invite_org.id, sample_user)

        # Verify membership with MEMBER
        args = membership_repo_mock.create.call_args[1]
        assert args["role"] == OrgRole.MEMBER

    @pytest.mark.asyncio
    async def test_consume_invite_exhausted_does_nothing(
        self, user_manager, sample_user, sample_invite_org, invite_repo_mock
    ):
        """Exhausted invite: do nothing."""
        sample_invite_org.is_exhausted = True
        invite_repo_mock.get.return_value = sample_invite_org

        await user_manager._consume_invite_by_id(sample_invite_org.id, sample_user)

        # No save
        invite_repo_mock.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_consume_invite_nonexistent_does_nothing(
        self, user_manager, sample_user, invite_repo_mock
    ):
        """Nonexistent invite: ignore silently."""
        invite_repo_mock.get.return_value = None

        await user_manager._consume_invite_by_id(uuid.uuid4(), sample_user)

        # No save
        invite_repo_mock.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_consume_invite_increments_uses(
        self,
        user_manager,
        sample_user,
        sample_invite_org,
        invite_repo_mock,
        user_repo_mock,
        membership_repo_mock,
    ):
        """Consumption increments uses."""
        initial_uses = sample_invite_org.uses

        invite_repo_mock.get.return_value = sample_invite_org
        user_repo_mock.get.return_value = sample_user
        membership_repo_mock.get_by_user_and_org.return_value = None

        await user_manager._consume_invite_by_id(sample_invite_org.id, sample_user)

        assert sample_invite_org.uses == initial_uses + 1
        invite_repo_mock.save.assert_called_once_with(sample_invite_org)

    @pytest.mark.asyncio
    async def test_consume_invite_member_can_upgrade_to_admin(
        self,
        user_manager,
        sample_user,
        sample_invite_org,
        sample_membership,
        invite_repo_mock,
        user_repo_mock,
        membership_repo_mock,
    ):
        sample_membership.user_id = sample_user.id
        sample_membership.organization_id = sample_invite_org.organization_id
        sample_membership.role = OrgRole.MEMBER

        sample_invite_org.role = OrgRole.ADMIN

        invite_repo_mock.get.return_value = sample_invite_org
        user_repo_mock.get.return_value = sample_user
        membership_repo_mock.get_by_user_and_org.return_value = sample_membership

        await user_manager._consume_invite_by_id(sample_invite_org.id, sample_user)

        membership_repo_mock.create.assert_not_called()
        membership_repo_mock.save.assert_called_once_with(sample_membership)
        invite_repo_mock.save.assert_called_once_with(sample_invite_org)

        assert sample_membership.role == OrgRole.ADMIN
