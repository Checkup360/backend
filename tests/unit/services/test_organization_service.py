import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.organization import OrganizationService


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

    with pytest.raises(ValueError) as exc:
        await service.create_organization("Acme 2", "acme")

    assert str(exc.value) == "organization_slug_already_exists"
    repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_list_organizations():
    repo = AsyncMock()
    repo.list.return_value = [MagicMock(name="Org 1"), MagicMock(name="Org 2")]

    service = OrganizationService(repo)
    orgs = await service.list_organizations()

    assert len(orgs) == 2
    repo.list.assert_awaited_once()
