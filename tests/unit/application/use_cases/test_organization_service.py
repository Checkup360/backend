import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domain.exceptions import OrganizationSlugAlreadyExists
from app.application.use_cases.organizations.organization_service import (
    OrganizationService,
)


@pytest.mark.asyncio
async def test_create_organization_success():
    repo = AsyncMock()
    repo.get_by_slug.return_value = None
    org_mock = MagicMock()
    org_mock.name = "Acme"
    org_mock.slug = "acme"
    repo.create.return_value = org_mock

    service = OrganizationService(repo)
    org = await service.create_organization("Acme", "acme")

    assert org.name == "Acme"
    repo.create.assert_awaited_once_with(name="Acme", slug="acme")


@pytest.mark.asyncio
async def test_create_organization_duplicate_slug_raises_error():
    repo = AsyncMock()
    repo.get_by_slug.return_value = MagicMock(slug="acme")

    service = OrganizationService(repo)

    with pytest.raises(OrganizationSlugAlreadyExists):
        await service.create_organization("Acme 2", "acme")

    repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_list_organizations():
    repo = AsyncMock()
    org_1 = MagicMock(name="Org 1")
    org_1.collaborators_count = 5
    org_2 = MagicMock(name="Org 2")
    org_2.collaborators_count = 0
    repo.list.return_value = [org_1, org_2]

    service = OrganizationService(repo)
    orgs = await service.list_organizations()

    assert len(orgs) == 2
    assert orgs[0].collaborators_count == 5
    assert orgs[1].collaborators_count == 0
    repo.list.assert_awaited_once()
