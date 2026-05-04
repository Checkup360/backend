import uuid

import pytest

from app.models import Organization


class TestOrganizations:
    @pytest.mark.asyncio
    async def test_superuser_can_create_organization(
        self, client, db_session_maker, make_user, override_current_user
    ):
        user = await make_user(is_superuser=True)
        override_current_user(user)

        response = client.post(
            "/organizations/",
            json={"name": "Acme", "slug": "acme"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Acme"
        assert data["slug"] == "acme"

        async with db_session_maker() as session:
            organization = await session.get(Organization, uuid.UUID(data["id"]))
        assert organization is not None

    @pytest.mark.asyncio
    async def test_non_superuser_cannot_create_organization(
        self, client, make_user, override_current_user
    ):
        user = await make_user(is_superuser=False)
        override_current_user(user)

        response = client.post(
            "/organizations/",
            json={"name": "Acme", "slug": "acme"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_organization_with_used_slug_returns_conflict(
        self, client, make_user, make_organization, override_current_user
    ):
        user = await make_user(is_superuser=True)
        await make_organization(slug="used-slug")
        override_current_user(user)

        response = client.post(
            "/organizations/",
            json={"name": "Other Org", "slug": "used-slug"},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "organization_slug_already_exists"
