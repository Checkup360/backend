import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.auth.authorization import (
    require_organization_admin,
    require_superuser,
    require_org_admin_any,
)
from app.models.membership import OrgRole


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
    organization_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4())
    request = MagicMock()
    request.json = AsyncMock(return_value={"organization_id": str(organization_id)})
    membership = SimpleNamespace(role=OrgRole.ADMIN)

    org_repo = AsyncMock()
    org_repo.get.return_value = SimpleNamespace(id=organization_id)
    membership_repo = AsyncMock()
    membership_repo.get_by_user_and_org.return_value = membership

    result = await require_organization_admin(request, org_repo, membership_repo, user)

    assert result is membership
    org_repo.get.assert_awaited_once_with(organization_id)
    membership_repo.get_by_user_and_org.assert_awaited_once_with(
        user.id, organization_id
    )


@pytest.mark.asyncio
async def test_require_organization_admin_rejects_missing_organization_id():
    request = MagicMock()
    request.json = AsyncMock(return_value={})

    with pytest.raises(HTTPException) as exc_info:
        await require_organization_admin(
            request, AsyncMock(), AsyncMock(), SimpleNamespace()
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "organization_id_required"


@pytest.mark.asyncio
async def test_require_organization_admin_rejects_invalid_organization_id():
    request = MagicMock()
    request.json = AsyncMock(return_value={"organization_id": "not-a-uuid"})

    with pytest.raises(HTTPException) as exc_info:
        await require_organization_admin(
            request, AsyncMock(), AsyncMock(), SimpleNamespace()
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid_organization_id"


@pytest.mark.asyncio
async def test_require_organization_admin_rejects_missing_organization():
    request = MagicMock()
    request.json = AsyncMock(return_value={"organization_id": str(uuid.uuid4())})
    org_repo = AsyncMock()
    org_repo.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await require_organization_admin(
            request, org_repo, AsyncMock(), SimpleNamespace()
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "organization_not_found"


@pytest.mark.asyncio
async def test_require_organization_admin_rejects_non_admin_membership():
    organization_id = uuid.uuid4()
    request = MagicMock()
    request.json = AsyncMock(return_value={"organization_id": str(organization_id)})

    org_repo = AsyncMock()
    org_repo.get.return_value = SimpleNamespace()

    membership_repo = AsyncMock()
    membership_repo.get_by_user_and_org.return_value = SimpleNamespace(
        role=OrgRole.MEMBER
    )

    with pytest.raises(HTTPException) as exc_info:
        await require_organization_admin(
            request, org_repo, membership_repo, SimpleNamespace(id=uuid.uuid4())
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


@pytest.mark.asyncio
async def test_require_org_admin_any_returns_user_with_admin_membership():
    user = SimpleNamespace(id=uuid.uuid4())
    membership_repo = AsyncMock()
    membership_repo.is_admin_of_any.return_value = True

    result = await require_org_admin_any(membership_repo, user)

    assert result is user
    membership_repo.is_admin_of_any.assert_awaited_once_with(user.id)


@pytest.mark.asyncio
async def test_require_org_admin_any_rejects_user_without_admin_membership():
    user = SimpleNamespace(id=uuid.uuid4())
    membership_repo = AsyncMock()
    membership_repo.is_admin_of_any.return_value = False

    with pytest.raises(HTTPException) as exc_info:
        await require_org_admin_any(membership_repo, user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"
