import uuid
import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException

from app.application.dto import AuthenticatedUser
from app.domain.entities import Membership, OrgRole
from app.presentation.api.authorization import (
    require_completed_member_onboarding,
    require_content_manager_or_above,
    require_org_admin_any,
    require_organization_admin,
    require_organization_admin_or_sysadmin,
    require_superuser,
)


def make_user(
    is_superuser: bool = False,
    membership: Membership | None = None,
) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid.uuid4(),
        email="test@example.com",
        is_superuser=is_superuser,
        membership=membership,
    )


class TestAuthorizationDependencies:
    def test_require_superuser_success(self):
        user = make_user(is_superuser=True)
        res = require_superuser(user)
        assert res == user

    def test_require_superuser_forbidden(self):
        user = make_user(is_superuser=False)
        with pytest.raises(HTTPException) as exc_info:
            require_superuser(user)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "forbidden"

    @pytest.mark.asyncio
    async def test_require_organization_admin_success(self):
        membership = Membership(
            user_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            roles=[OrgRole.ADMIN],
        )
        user = make_user(membership=membership)
        result = await require_organization_admin(user)
        assert result == membership

    @pytest.mark.asyncio
    async def test_require_organization_admin_no_membership_forbidden(self):
        user = make_user(membership=None)
        with pytest.raises(HTTPException) as exc_info:
            await require_organization_admin(user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_organization_admin_member_role_forbidden(self):
        membership = Membership(
            user_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            roles=[OrgRole.MEMBER],
        )
        user = make_user(membership=membership)
        with pytest.raises(HTTPException) as exc_info:
            await require_organization_admin(user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_org_admin_any(self):
        service = AsyncMock()
        service.is_admin_of_any.return_value = True
        user = make_user()

        res = await require_org_admin_any(membership_service=service, current_user=user)
        assert res == user

        service.is_admin_of_any.return_value = False
        with pytest.raises(HTTPException) as exc_info:
            await require_org_admin_any(membership_service=service, current_user=user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_completed_member_onboarding(self):
        service = AsyncMock()
        user = make_user()

        service.requires_onboarding.return_value = False
        res = await require_completed_member_onboarding(
            member_details_service=service, current_user=user
        )
        assert res == user

        service.requires_onboarding.return_value = True
        with pytest.raises(HTTPException) as exc_info:
            await require_completed_member_onboarding(
                member_details_service=service, current_user=user
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "onboarding_required"

    @pytest.mark.asyncio
    async def test_require_organization_admin_or_sysadmin(self):
        sysadmin = make_user(is_superuser=True)
        res_sysadmin = await require_organization_admin_or_sysadmin(sysadmin)
        assert res_sysadmin == sysadmin

        membership = Membership(
            user_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            roles=[OrgRole.ADMIN],
        )
        org_admin = make_user(is_superuser=False, membership=membership)
        res_admin = await require_organization_admin_or_sysadmin(org_admin)
        assert res_admin == membership


class TestRequireContentManagerOrAbove:
    @pytest.mark.asyncio
    async def test_admin_is_allowed(self):
        membership = Membership(
            user_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            roles=[OrgRole.ADMIN],
        )
        user = make_user(membership=membership)
        result = await require_content_manager_or_above(user)
        assert result == membership

    @pytest.mark.asyncio
    async def test_content_manager_is_allowed(self):
        membership = Membership(
            user_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            roles=[OrgRole.CONTENT_MANAGER],
        )
        user = make_user(membership=membership)
        result = await require_content_manager_or_above(user)
        assert result == membership

    @pytest.mark.asyncio
    async def test_member_is_forbidden(self):
        membership = Membership(
            user_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            roles=[OrgRole.MEMBER],
        )
        user = make_user(membership=membership)
        with pytest.raises(HTTPException) as exc_info:
            await require_content_manager_or_above(user)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "forbidden"

    @pytest.mark.asyncio
    async def test_no_membership_is_forbidden(self):
        user = make_user(membership=None)
        with pytest.raises(HTTPException) as exc_info:
            await require_content_manager_or_above(user)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "forbidden"
