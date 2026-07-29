from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
import uuid
from datetime import datetime, timezone

from app.domain.entities import InviteToken
from app.domain.value_objects.org_role import OrgRole


class TestInviteTokenFromRequest:
    """Tests for extracting the invite token from the request."""

    def test_token_from_override(self, user_manager, request_mock):
        request_mock.state.invite_token_override = "override-token"
        token = user_manager._invite_token_from_request(request_mock)
        assert token == "override-token"

    def test_token_from_cookie(self, user_manager, request_mock):
        request_mock.cookies = {"pending_invite": "cookie-token"}
        token = user_manager._invite_token_from_request(request_mock)
        assert token == "cookie-token"

    def test_override_takes_priority_over_cookie(self, user_manager, request_mock):
        request_mock.state.invite_token_override = "override-token"
        request_mock.cookies = {"pending_invite": "cookie-token"}
        token = user_manager._invite_token_from_request(request_mock)
        assert token == "override-token"

    def test_no_token_fails(self, user_manager, request_mock):
        with pytest.raises(HTTPException) as exc_info:
            user_manager._invite_token_from_request(request_mock)
        assert exc_info.value.status_code == 303

    def test_no_request_fails(self, user_manager):
        with pytest.raises(HTTPException):
            user_manager._invite_token_from_request(None)


class TestHasInviteToken:
    """Tests for checking whether a token exists without failing."""

    def test_has_invite_token_with_override(self, user_manager, request_mock):
        request_mock.state.invite_token_override = "token"
        assert user_manager._has_invite_token(request_mock) is True

    def test_has_invite_token_with_cookie(self, user_manager, request_mock):
        request_mock.cookies = {"pending_invite": "token"}
        assert user_manager._has_invite_token(request_mock) is True

    def test_no_invite_token(self, user_manager, request_mock):
        assert user_manager._has_invite_token(request_mock) is False

    def test_no_request_returns_false(self, user_manager):
        assert user_manager._has_invite_token(None) is False


class TestInviteFail:
    """Tests for invite error handling."""

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
        assert isinstance(exc_info.value.detail, dict)

    def test_invite_fail_sets_clear_cookie_flag(self, user_manager, request_mock):
        try:
            user_manager._invite_fail(request_mock, "no_invite")
        except HTTPException:
            pass
        assert request_mock.state.clear_pending_invite_cookie is True

    def test_invite_fail_no_request(self, user_manager):
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

        membership_repo_mock.save.assert_called_once()
        saved = membership_repo_mock.save.call_args[0][0]
        assert saved.user_id == sample_user.id
        assert saved.organization_id == sample_invite_org.organization_id
        assert saved.roles == [OrgRole.MEMBER]

        invite_repo_mock.update.assert_called_once_with(sample_invite_org.id, uses=1)

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
        """ADMIN user: adds MEMBER role when consuming a MEMBER invite."""
        sample_invite_org.role = OrgRole.MEMBER
        invite_repo_mock.get.return_value = sample_invite_org
        user_repo_mock.get.return_value = sample_user

        sample_membership.user_id = sample_user.id
        sample_membership.organization_id = sample_invite_org.organization_id
        sample_membership.roles = [OrgRole.ADMIN]
        membership_repo_mock.get_by_user_and_org.return_value = sample_membership

        await user_manager._consume_invite_by_id(sample_invite_org.id, sample_user)

        membership_repo_mock.create.assert_not_called()
        membership_repo_mock.save.assert_called_once()
        saved = membership_repo_mock.save.call_args[0][0]
        assert OrgRole.ADMIN in saved.roles
        assert OrgRole.MEMBER in saved.roles
        invite_repo_mock.update.assert_called_once_with(sample_invite_org.id, uses=1)

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

        user_repo_mock.update.assert_called_once_with(sample_user.id, is_superuser=True)

        invite_repo_mock.update.assert_called_once_with(
            sample_invite_sysadmin.id, uses=1
        )

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

        saved = membership_repo_mock.save.call_args[0][0]
        assert saved.roles == [OrgRole.MEMBER]

    @pytest.mark.asyncio
    async def test_consume_invite_exhausted_does_nothing(
        self, user_manager, sample_user, invite_repo_mock
    ):
        """Exhausted invite: do nothing."""
        exhausted = InviteToken(
            id=uuid.uuid4(),
            token="exhausted",
            email=None,
            uses=1,
            max_uses=1,
            expires_at=datetime.now(timezone.utc),
        )
        invite_repo_mock.get.return_value = exhausted

        await user_manager._consume_invite_by_id(exhausted.id, sample_user)

        invite_repo_mock.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_consume_invite_nonexistent_does_nothing(
        self, user_manager, sample_user, invite_repo_mock
    ):
        """Nonexistent invite: ignore silently."""
        invite_repo_mock.get.return_value = None

        await user_manager._consume_invite_by_id(uuid.uuid4(), sample_user)

        invite_repo_mock.update.assert_not_called()

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
        invite_repo_mock.get.return_value = sample_invite_org
        user_repo_mock.get.return_value = sample_user
        membership_repo_mock.get_by_user_and_org.return_value = None

        await user_manager._consume_invite_by_id(sample_invite_org.id, sample_user)

        invite_repo_mock.update.assert_called_once_with(sample_invite_org.id, uses=1)

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
        sample_invite_org.role = OrgRole.ADMIN
        invite_repo_mock.get.return_value = sample_invite_org

        user_repo_mock.get.return_value = sample_user

        sample_membership.user_id = sample_user.id
        sample_membership.organization_id = sample_invite_org.organization_id
        sample_membership.roles = [OrgRole.MEMBER]
        membership_repo_mock.get_by_user_and_org.return_value = sample_membership

        await user_manager._consume_invite_by_id(sample_invite_org.id, sample_user)

        membership_repo_mock.create.assert_not_called()
        membership_repo_mock.save.assert_called_once()
        saved = membership_repo_mock.save.call_args[0][0]
        assert OrgRole.ADMIN in saved.roles
        invite_repo_mock.update.assert_called_once_with(sample_invite_org.id, uses=1)


class TestUserManagerCallbacks:
    @pytest.mark.asyncio
    async def test_on_after_forgot_password(self, user_manager, sample_user):
        mock_reset = AsyncMock()
        user_manager.request_password_reset = mock_reset

        await user_manager.on_after_forgot_password(sample_user, "reset_token_123")

        mock_reset.execute.assert_awaited_once_with(
            "user@example.com", "reset_token_123"
        )

    @pytest.mark.asyncio
    async def test_validate_password_policy_rejection(self, user_manager, sample_user):
        mock_policy = MagicMock()
        mock_policy.get_validation_error.return_value = "Password too simple"
        user_manager.password_reset_policy = mock_policy

        from fastapi_users import exceptions

        with pytest.raises(exceptions.InvalidPasswordException) as exc_info:
            await user_manager.validate_password("weak", sample_user)
        assert exc_info.value.reason == "Password too simple"

    @pytest.mark.asyncio
    async def test_on_after_login_consumes_invite_and_clears_cookie(
        self, user_manager, sample_user, request_mock, invite_repo_mock, user_repo_mock
    ):
        invite_id = uuid.uuid4()
        request_mock.state.invite_pending_consumption_id = invite_id
        request_mock.cookies = {"pending_invite": "cookie_val"}

        invite_repo_mock.get.return_value = InviteToken(
            id=invite_id,
            token="cookie_val",
            uses=0,
            max_uses=1,
            expires_at=datetime.now(timezone.utc),
            is_sysadmin=True,
        )
        user_repo_mock.get.return_value = sample_user

        response = MagicMock()
        response.delete_cookie = MagicMock()

        await user_manager.on_after_login(sample_user, request_mock, response)

        assert getattr(request_mock.state, "invite_pending_consumption_id") is None
        response.delete_cookie.assert_called_once()

    @pytest.mark.asyncio
    async def test_assert_invite_valid_for_email_raises_invite_fail(
        self, user_manager, request_mock, invite_repo_mock
    ):
        from app.domain.exceptions import InviteExpiredError

        request_mock.cookies = {"pending_invite": "expired_token"}
        user_manager.invite_service.validate_invite = AsyncMock(
            side_effect=InviteExpiredError()
        )

        with pytest.raises(HTTPException) as exc_info:
            await user_manager._assert_invite_valid_for_email(
                request_mock, "user@example.com"
            )

        assert exc_info.value.status_code == 303
        assert "invite_expired" in exc_info.value.headers.get("Location", "")

    @pytest.mark.asyncio
    async def test_oauth_callback_existing_user_with_invite(
        self, user_manager, sample_user, request_mock, sample_invite_org
    ):
        user_manager.user_db.get_by_oauth_account = AsyncMock(return_value=sample_user)
        user_manager._assert_invite_valid_for_email = AsyncMock(
            return_value=sample_invite_org
        )
        user_manager._has_invite_token = MagicMock(return_value=True)

        with patch(
            "fastapi_users.BaseUserManager.oauth_callback", new_callable=AsyncMock
        ) as mock_super_oauth:
            mock_super_oauth.return_value = sample_user
            res = await user_manager.oauth_callback(
                "google", "token", "acc123", "user@example.com", request=request_mock
            )
            assert res == sample_user
            assert (
                request_mock.state.invite_pending_consumption_id == sample_invite_org.id
            )

    @pytest.mark.asyncio
    async def test_oauth_callback_new_user(
        self, user_manager, sample_user, request_mock, sample_invite_org
    ):
        user_manager.user_db.get_by_oauth_account = AsyncMock(return_value=None)
        user_manager._assert_invite_valid_for_email = AsyncMock(
            return_value=sample_invite_org
        )

        with patch(
            "fastapi_users.BaseUserManager.oauth_callback", new_callable=AsyncMock
        ) as mock_super_oauth:
            mock_super_oauth.return_value = sample_user
            res = await user_manager.oauth_callback(
                "google", "token", "acc123", "user@example.com", request=request_mock
            )
            assert res == sample_user
            assert request_mock.state.invite_already_validated is True

    @pytest.mark.asyncio
    async def test_create_user_with_invite_and_consume(
        self, user_manager, sample_user, request_mock, sample_invite_org
    ):
        user_create = MagicMock()
        user_create.email = "new@example.com"
        user_manager._assert_invite_valid_for_email = AsyncMock(
            return_value=sample_invite_org
        )
        user_manager._consume_invite_by_id = AsyncMock()

        with patch(
            "fastapi_users.BaseUserManager.create", new_callable=AsyncMock
        ) as mock_super_create:
            mock_super_create.return_value = sample_user
            created = await user_manager.create(user_create, request=request_mock)
            assert created == sample_user
            user_manager._consume_invite_by_id.assert_called_once_with(
                sample_invite_org.id, sample_user
            )

    @pytest.mark.asyncio
    async def test_create_user_exception_clears_pending_invite_id(
        self, user_manager, request_mock, sample_invite_org
    ):
        user_create = MagicMock()
        user_create.email = "new@example.com"
        user_manager._assert_invite_valid_for_email = AsyncMock(
            return_value=sample_invite_org
        )

        with patch(
            "fastapi_users.BaseUserManager.create", new_callable=AsyncMock
        ) as mock_super_create:
            mock_super_create.side_effect = Exception("User creation failed")
            with pytest.raises(Exception, match="User creation failed"):
                await user_manager.create(user_create, request=request_mock)
            assert (
                getattr(request_mock.state, "invite_pending_consumption_id", None)
                is None
            )
