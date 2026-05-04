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
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(id=organization_id)
    db.scalar.return_value = membership

    result = await require_organization_admin(request, db, user)

    assert result is membership
    db.get.assert_awaited_once()
    db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_require_organization_admin_rejects_missing_organization_id():
    request = MagicMock()
    request.json = AsyncMock(return_value={})

    with pytest.raises(HTTPException) as exc_info:
        await require_organization_admin(request, AsyncMock(), SimpleNamespace())

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "organization_id_required"


@pytest.mark.asyncio
async def test_require_organization_admin_rejects_invalid_organization_id():
    request = MagicMock()
    request.json = AsyncMock(return_value={"organization_id": "not-a-uuid"})

    with pytest.raises(HTTPException) as exc_info:
        await require_organization_admin(request, AsyncMock(), SimpleNamespace())

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid_organization_id"


@pytest.mark.asyncio
async def test_require_organization_admin_rejects_missing_organization():
    request = MagicMock()
    request.json = AsyncMock(return_value={"organization_id": str(uuid.uuid4())})
    db = AsyncMock()
    db.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await require_organization_admin(request, db, SimpleNamespace())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "organization_not_found"


@pytest.mark.asyncio
async def test_require_organization_admin_rejects_non_admin_membership():
    request = MagicMock()
    request.json = AsyncMock(return_value={"organization_id": str(uuid.uuid4())})
    db = AsyncMock()
    db.get.return_value = SimpleNamespace()
    db.scalar.return_value = SimpleNamespace(role=OrgRole.MEMBER)

    with pytest.raises(HTTPException) as exc_info:
        await require_organization_admin(request, db, SimpleNamespace(id=uuid.uuid4()))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


@pytest.mark.asyncio
async def test_require_org_admin_any_returns_user_with_admin_membership():
    user = SimpleNamespace(id=uuid.uuid4())
    db = AsyncMock()
    db.scalar.return_value = SimpleNamespace(role=OrgRole.ADMIN)

    result = await require_org_admin_any(db, user)

    assert result is user
    db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_require_org_admin_any_rejects_user_without_admin_membership():
    user = SimpleNamespace(id=uuid.uuid4())
    db = AsyncMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await require_org_admin_any(db, user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"
