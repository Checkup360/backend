"""
Unit tests for UserManager and invite logic.
"""

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock
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
        self, user_manager, request_mock, sample_user, sample_invite_org
    ):
        """New user: create membership with the invite role."""
        request_mock.state.db = AsyncMock()
        request_mock.state.db.get = AsyncMock(
            side_effect=[sample_invite_org, sample_user]
        )
        request_mock.state.db.scalar = AsyncMock(return_value=None)
        request_mock.state.db.add = MagicMock()
        request_mock.state.db.commit = AsyncMock()

        await user_manager._consume_invite_by_id(
            request_mock, sample_invite_org.id, sample_user
        )

        # Verify the membership was created
        request_mock.state.db.add.assert_called_once()
        added_membership = request_mock.state.db.add.call_args[0][0]
        assert added_membership.user_id == sample_user.id
        assert added_membership.organization_id == sample_invite_org.organization_id
        assert added_membership.role == OrgRole.MEMBER

        # Verify the invite was consumed
        assert sample_invite_org.uses == 1
        request_mock.state.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_consume_invite_admin_preserves_role(
        self,
        user_manager,
        request_mock,
        sample_user,
        sample_invite_org,
        sample_membership,
    ):
        """ADMIN user: does NOT downgrade role when consuming a MEMBER invite."""
        # Setup: user is ADMIN in the org
        sample_membership.user_id = sample_user.id
        sample_membership.organization_id = sample_invite_org.organization_id
        sample_membership.role = OrgRole.ADMIN

        # Invite attempts to assign MEMBER
        sample_invite_org.role = OrgRole.MEMBER

        request_mock.state.db = AsyncMock()
        request_mock.state.db.get = AsyncMock(
            side_effect=[sample_invite_org, sample_user]
        )
        request_mock.state.db.scalar = AsyncMock(return_value=sample_membership)
        request_mock.state.db.add = MagicMock()
        request_mock.state.db.commit = AsyncMock()

        await user_manager._consume_invite_by_id(
            request_mock, sample_invite_org.id, sample_user
        )

        # Verify no membership was added
        request_mock.state.db.add.assert_not_called()

        # Verify the role remained ADMIN
        assert sample_membership.role == OrgRole.ADMIN

        # Verify the invite was not consumed
        assert sample_invite_org.uses == 0
        request_mock.state.db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_consume_invite_sysadmin_sets_superuser(
        self, user_manager, request_mock, sample_user, sample_invite_sysadmin
    ):
        """Sysadmin invite sets user.is_superuser = True."""
        request_mock.state.db = AsyncMock()
        request_mock.state.db.get = AsyncMock(
            side_effect=[sample_invite_sysadmin, sample_user]
        )
        request_mock.state.db.commit = AsyncMock()

        await user_manager._consume_invite_by_id(
            request_mock, sample_invite_sysadmin.id, sample_user
        )

        # Verify superuser
        assert sample_user.is_superuser is True

        # Verify the invite was consumed
        assert sample_invite_sysadmin.uses == 1
        request_mock.state.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_consume_invite_default_member_role(
        self, user_manager, request_mock, sample_user, sample_invite_org
    ):
        """Invite without a role uses MEMBER by default."""
        sample_invite_org.role = None

        request_mock.state.db = AsyncMock()
        request_mock.state.db.get = AsyncMock(
            side_effect=[sample_invite_org, sample_user]
        )
        request_mock.state.db.scalar = AsyncMock(return_value=None)
        request_mock.state.db.add = MagicMock()
        request_mock.state.db.commit = AsyncMock()

        await user_manager._consume_invite_by_id(
            request_mock, sample_invite_org.id, sample_user
        )

        # Verify membership with MEMBER
        added_membership = request_mock.state.db.add.call_args[0][0]
        assert added_membership.role == OrgRole.MEMBER

    @pytest.mark.asyncio
    async def test_consume_invite_exhausted_does_nothing(
        self, user_manager, request_mock, sample_user, sample_invite_org
    ):
        """Exhausted invite: do nothing."""
        sample_invite_org.is_exhausted = True

        request_mock.state.db = AsyncMock()
        request_mock.state.db.get = AsyncMock(return_value=sample_invite_org)
        request_mock.state.db.commit = AsyncMock()

        await user_manager._consume_invite_by_id(
            request_mock, sample_invite_org.id, sample_user
        )

        # No commit
        request_mock.state.db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_consume_invite_nonexistent_does_nothing(
        self, user_manager, request_mock, sample_user
    ):
        """Nonexistent invite: ignore silently."""
        request_mock.state.db = AsyncMock()
        request_mock.state.db.get = AsyncMock(return_value=None)
        request_mock.state.db.commit = AsyncMock()

        await user_manager._consume_invite_by_id(
            request_mock, uuid.uuid4(), sample_user
        )

        # No commit
        request_mock.state.db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_consume_invite_increments_uses(
        self, user_manager, request_mock, sample_user, sample_invite_org
    ):
        """Consumption increments uses."""
        initial_uses = sample_invite_org.uses

        request_mock.state.db = AsyncMock()
        request_mock.state.db.get = AsyncMock(
            side_effect=[sample_invite_org, sample_user]
        )
        request_mock.state.db.scalar = AsyncMock(return_value=None)
        request_mock.state.db.add = MagicMock()
        request_mock.state.db.commit = AsyncMock()

        await user_manager._consume_invite_by_id(
            request_mock, sample_invite_org.id, sample_user
        )

        assert sample_invite_org.uses == initial_uses + 1

    @pytest.mark.asyncio
    async def test_consume_invite_member_can_upgrade_to_admin(
        self,
        user_manager,
        request_mock,
        sample_user,
        sample_invite_org,
        sample_membership,
    ):
        sample_membership.user_id = sample_user.id
        sample_membership.organization_id = sample_invite_org.organization_id
        sample_membership.role = OrgRole.MEMBER

        sample_invite_org.role = OrgRole.ADMIN

        request_mock.state.db = AsyncMock()
        request_mock.state.db.get = AsyncMock(
            side_effect=[sample_invite_org, sample_user]
        )
        request_mock.state.db.scalar = AsyncMock(return_value=sample_membership)
        request_mock.state.db.add = MagicMock()
        request_mock.state.db.commit = AsyncMock()

        await user_manager._consume_invite_by_id(
            request_mock, sample_invite_org.id, sample_user
        )

        request_mock.state.db.add.assert_not_called()
        request_mock.state.db.commit.assert_called_once()

        assert sample_membership.role == OrgRole.ADMIN
