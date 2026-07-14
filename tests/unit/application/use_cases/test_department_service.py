import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.entities.department import Department
from app.domain.exceptions import DepartmentSlugAlreadyExists
from app.application.use_cases.departments import DepartmentService
from app.domain.services.department_policy import build_department_slug


def test_build_department_slug_normalizes_name():
    assert build_department_slug("  People Operations  ") == "people-operations"


@pytest.mark.asyncio
async def test_create_department_normalizes_slug_and_checks_admin():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    user_id = uuid.uuid4()
    organization_id = uuid.uuid4()
    created = Department(
        id=uuid.uuid4(),
        organization_id=organization_id,
        name="People Operations",
        slug="people-operations",
    )
    department_repo.get_by_organization_and_slug.return_value = None
    department_repo.create.return_value = created

    service = DepartmentService(department_repo, membership_service, membership_repo)
    result = await service.create_department(
        user_id, organization_id, "People Operations"
    )

    assert result == created
    membership_service.get_admin_membership.assert_awaited_once_with(
        user_id, organization_id
    )
    department_repo.create.assert_awaited_once()
    assert department_repo.create.call_args.kwargs["slug"] == "people-operations"


@pytest.mark.asyncio
async def test_create_department_rejects_duplicate_slug():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    organization_id = uuid.uuid4()
    department_repo.get_by_organization_and_slug.return_value = MagicMock()

    service = DepartmentService(department_repo, membership_service, membership_repo)

    with pytest.raises(DepartmentSlugAlreadyExists):
        await service.create_department(uuid.uuid4(), organization_id, "People")
