import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.auth.authorization import (
    require_completed_member_onboarding,
    require_organization_admin,
    require_superuser,
    require_org_admin_any,
)
from app.domain.entities.org_role import OrgRole


def test_require_superuser_returns_user():
    user = SimpleNamespace(is_superuser=True)

    assert require_superuser(user) is user


def test_require_superuser_rejects_non_superuser():
    user = SimpleNamespace(is_superuser=False)

    with pytest.raises(HTTPException) as exc_info:
        require_superuser(user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


@pytest.mark.asyncio
async def test_require_organization_admin_returns_admin_membership():
    user = SimpleNamespace(
        id=uuid.uuid4(),
        membership=SimpleNamespace(
            roles=[OrgRole.ADMIN],
            organization_id=uuid.uuid4(),
            organization=SimpleNamespace(name="Test Org"),
        ),
    )

    result = await require_organization_admin(user)

    assert result is user.membership


@pytest.mark.asyncio
async def test_require_organization_admin_rejects_missing_organization_id():
    user = SimpleNamespace(membership=None)

    with pytest.raises(HTTPException) as exc_info:
        await require_organization_admin(user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


@pytest.mark.asyncio
async def test_require_organization_admin_rejects_invalid_organization_id():
    user = SimpleNamespace(
        membership=SimpleNamespace(
            roles=[OrgRole.MEMBER],
            organization_id=uuid.uuid4(),
            organization=SimpleNamespace(name="Test Org"),
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        await require_organization_admin(user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


@pytest.mark.asyncio
async def test_require_organization_admin_rejects_missing_organization():
    user = SimpleNamespace(membership=None)

    with pytest.raises(HTTPException) as exc_info:
        await require_organization_admin(user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


@pytest.mark.asyncio
async def test_require_organization_admin_rejects_non_admin_membership():
    user = SimpleNamespace(
        membership=SimpleNamespace(
            roles=[OrgRole.MEMBER],
            organization_id=uuid.uuid4(),
            organization=SimpleNamespace(name="Test Org"),
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        await require_organization_admin(user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


@pytest.mark.asyncio
async def test_require_org_admin_any_returns_user_with_admin_membership():
    user = SimpleNamespace(id=uuid.uuid4())
    membership_service = AsyncMock()
    membership_service.is_admin_of_any.return_value = True

    result = await require_org_admin_any(membership_service, user)

    assert result is user
    membership_service.is_admin_of_any.assert_awaited_once_with(user.id)


@pytest.mark.asyncio
async def test_require_org_admin_any_rejects_user_without_admin_membership():
    user = SimpleNamespace(id=uuid.uuid4())
    membership_service = AsyncMock()
    membership_service.is_admin_of_any.return_value = False

    with pytest.raises(HTTPException) as exc_info:
        await require_org_admin_any(membership_service, user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


@pytest.mark.asyncio
async def test_require_completed_member_onboarding_returns_user_when_completed():
    user = SimpleNamespace(id=uuid.uuid4())
    member_details_service = AsyncMock()
    member_details_service.requires_onboarding.return_value = False

    result = await require_completed_member_onboarding(member_details_service, user)

    assert result is user
    member_details_service.requires_onboarding.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_require_completed_member_onboarding_rejects_pending_user():
    user = SimpleNamespace(id=uuid.uuid4())
    member_details_service = AsyncMock()
    member_details_service.requires_onboarding.return_value = True

    with pytest.raises(HTTPException) as exc_info:
        await require_completed_member_onboarding(member_details_service, user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "onboarding_required"
