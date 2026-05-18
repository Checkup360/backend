import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.repositories.organization import OrganizationRepository


@pytest.mark.asyncio
async def test_create_organization(db: AsyncSession):
    repo = OrganizationRepository(db)
    org = await repo.create(name="Test Org", slug="test-org")

    assert org.id is not None
    assert org.name == "Test Org"
    assert org.slug == "test-org"


@pytest.mark.asyncio
async def test_get_by_slug(db: AsyncSession):
    repo = OrganizationRepository(db)
    await repo.create(name="Target", slug="target-slug")

    found = await repo.get_by_slug("target-slug")
    assert found is not None
    assert found.name == "Target"

    not_found = await repo.get_by_slug("non-existent")
    assert not_found is None


@pytest.mark.asyncio
async def test_list_organizations(db: AsyncSession):
    repo = OrganizationRepository(db)
    await repo.create(name="Org 1", slug="org-1")
    await repo.create(name="Org 2", slug="org-2")

    orgs = await repo.list()
    assert len(orgs) == 2
    assert {o.slug for o in orgs} == {"org-1", "org-2"}


@pytest.mark.asyncio
async def test_update_organization(db: AsyncSession):
    repo = OrganizationRepository(db)
    org = await repo.create(name="Original", slug="original")

    updated = await repo.update(org.id, name="Updated Name")
    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.slug == "original"


@pytest.mark.asyncio
async def test_delete_organization(db: AsyncSession):
    repo = OrganizationRepository(db)
    org = await repo.create(name="To Delete", slug="delete-me")

    success = await repo.delete(org.id)
    assert success is True

    found = await repo.get(org.id)
    assert found is None

    # Delete non-existent
    success_again = await repo.delete(uuid.uuid4())
    assert success_again is False
