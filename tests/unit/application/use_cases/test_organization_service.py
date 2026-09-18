import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domain.entities import OrganizationScoreWeights
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
async def test_create_organization_creates_initial_score_weights_v1():
    repo = AsyncMock()
    weights_repo = AsyncMock()
    repo.get_by_slug.return_value = None
    org_id = uuid.uuid4()
    org_mock = MagicMock()
    org_mock.id = org_id
    org_mock.name = "Acme"
    org_mock.slug = "acme"
    repo.create.return_value = org_mock

    service = OrganizationService(repo, score_weights_repo=weights_repo)
    org = await service.create_organization("Acme", "acme")

    assert org.name == "Acme"
    weights_repo.save.assert_awaited_once()
    saved_weights = weights_repo.save.call_args[0][0]
    assert saved_weights.organization_id == org_id
    assert saved_weights.version == 1
    assert saved_weights.changed_by_user_id is None
    assert "diabetes" in saved_weights.weights


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


@pytest.mark.asyncio
async def test_get_organization_returns_org_when_found():
    repo = AsyncMock()
    org_id = uuid.uuid4()
    org_mock = MagicMock(id=org_id, name="Found Org")
    repo.get.return_value = org_mock

    service = OrganizationService(repo)
    result = await service.get_organization(org_id)

    assert result == org_mock
    repo.get.assert_awaited_once_with(org_id)


@pytest.mark.asyncio
async def test_get_organization_returns_none_when_not_found():
    repo = AsyncMock()
    org_id = uuid.uuid4()
    repo.get.return_value = None

    service = OrganizationService(repo)
    result = await service.get_organization(org_id)

    assert result is None
    repo.get.assert_awaited_once_with(org_id)


@pytest.mark.asyncio
async def test_delete_organization_returns_true_on_success():
    repo = AsyncMock()
    org_id = uuid.uuid4()
    repo.delete.return_value = True

    service = OrganizationService(repo)
    result = await service.delete_organization(org_id)

    assert result is True
    repo.delete.assert_awaited_once_with(org_id)


@pytest.mark.asyncio
async def test_delete_organization_returns_false_when_not_found():
    repo = AsyncMock()
    org_id = uuid.uuid4()
    repo.delete.return_value = False

    service = OrganizationService(repo)
    result = await service.delete_organization(org_id)

    assert result is False
    repo.delete.assert_awaited_once_with(org_id)


@pytest.mark.asyncio
async def test_get_score_weights_returns_defaults_when_not_set():
    repo = AsyncMock()
    org_id = uuid.uuid4()
    org_mock = MagicMock(id=org_id, score_weights=None)
    repo.get.return_value = org_mock

    service = OrganizationService(repo)
    weights = await service.get_score_weights(org_id)

    assert weights == {"diabetes": 34.0, "sleep_apnea": 33.0, "depression": 33.0}


@pytest.mark.asyncio
async def test_update_score_weights_success():
    repo = AsyncMock()
    org_id = uuid.uuid4()
    org_mock = MagicMock(id=org_id, score_weights=None)
    repo.get.return_value = org_mock

    updated_mock = MagicMock(
        id=org_id, score_weights={"diabetes": 70.0, "sleep_apnea": 30.0}
    )
    repo.update_score_weights.return_value = updated_mock

    service = OrganizationService(repo)
    result = await service.update_score_weights(
        org_id, {"diabetes": 70.0, "sleep_apnea": 30.0}
    )

    assert result.score_weights == {"diabetes": 70.0, "sleep_apnea": 30.0}
    repo.update_score_weights.assert_awaited_once_with(
        org_id, {"diabetes": 70.0, "sleep_apnea": 30.0}
    )


@pytest.mark.asyncio
async def test_update_score_weights_saves_next_version():
    repo = AsyncMock()
    weights_repo = AsyncMock()
    org_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    org_mock = MagicMock(id=org_id, score_weights=None)
    repo.get.return_value = org_mock

    existing_v1 = OrganizationScoreWeights(
        id=uuid.uuid4(),
        organization_id=org_id,
        version=1,
        weights={"diabetes": 34.0},
        changed_by_user_id=None,
        created_at=MagicMock(),
    )
    weights_repo.get_active_for_organization.return_value = existing_v1

    updated_mock = MagicMock(
        id=org_id, score_weights={"cardiovascular": 60.0, "diabetes": 40.0}
    )
    repo.update_score_weights.return_value = updated_mock

    service = OrganizationService(repo, score_weights_repo=weights_repo)
    result = await service.update_score_weights(
        org_id,
        {"cardiovascular": 60.0, "diabetes": 40.0},
        changed_by_user_id=admin_id,
    )

    assert result.score_weights == {"cardiovascular": 60.0, "diabetes": 40.0}
    weights_repo.save.assert_awaited_once()
    saved_weights = weights_repo.save.call_args[0][0]
    assert saved_weights.organization_id == org_id
    assert saved_weights.version == 2
    assert saved_weights.weights == {"cardiovascular": 60.0, "diabetes": 40.0}
    assert saved_weights.changed_by_user_id == admin_id
