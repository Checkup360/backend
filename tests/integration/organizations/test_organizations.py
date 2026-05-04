import uuid

import pytest

from app.models import Organization


class TestOrganizations:
    @pytest.mark.asyncio
    async def test_superuser_can_create_organization(
        self, client, db_session_maker, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="superuser-create-org@example.com",
            is_superuser=True,
        )

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
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="regular-create-org@example.com",
            is_superuser=False,
        )

        response = client.post(
            "/organizations/",
            json={"name": "Acme", "slug": "acme"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_organization_with_used_slug_returns_conflict(
        self, client, make_organization, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="superuser-used-slug@example.com",
            is_superuser=True,
        )
        await make_organization(slug="used-slug")

        response = client.post(
            "/organizations/",
            json={"name": "Other Org", "slug": "used-slug"},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "organization_slug_already_exists"

    @pytest.mark.asyncio
    async def test_create_organization_with_empty_slug_returns_422(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="superuser-empty-slug@example.com",
            is_superuser=True,
        )

        response = client.post(
            "/organizations/",
            json={"name": "Acme", "slug": ""},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_organization_with_empty_name_returns_422(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="superuser-empty-name@example.com",
            is_superuser=True,
        )

        response = client.post(
            "/organizations/",
            json={"name": "", "slug": "acme"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_organization_with_invalid_slug_format_returns_422(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="superuser-invalid-slug@example.com",
            is_superuser=True,
        )

        invalid_slugs = [
            "Acme-Inc",  # uppercase
            "acme inc",  # spaces
            "acme@inc",  # special chars
            "acme_inc",  # underscore
            "-acme",  # starts with hyphen
            "acme-",  # ends with hyphen
            "acme--inc",  # double hyphen
        ]

        for slug in invalid_slugs:
            response = client.post(
                "/organizations/",
                json={"name": "Acme", "slug": slug},
            )
            assert response.status_code == 422, f"Slug '{slug}' should be invalid"

    @pytest.mark.asyncio
    async def test_create_organization_with_valid_slug_formats(
        self, client, auth_scenario, db_session_maker
    ):
        await auth_scenario.register_and_login(
            email="superuser-valid-slug@example.com",
            is_superuser=True,
        )

        valid_slugs = [
            "acme",
            "acme-inc",
            "acme-inc-123",
            "a",
            "a1b2c3",
        ]

        for slug in valid_slugs:
            response = client.post(
                "/organizations/",
                json={"name": f"Test Org {slug}", "slug": slug},
            )
            assert response.status_code == 201, f"Slug '{slug}' should be valid"
            assert response.json()["slug"] == slug

    @pytest.mark.asyncio
    async def test_superuser_can_list_organizations(
        self, client, make_organization, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="superuser-list-orgs@example.com",
            is_superuser=True,
        )
        await make_organization(name="Org 1", slug="org-1")
        await make_organization(name="Org 2", slug="org-2")

        response = client.get("/organizations/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(o["slug"] == "org-1" for o in data)
        assert any(o["slug"] == "org-2" for o in data)

    @pytest.mark.asyncio
    async def test_non_superuser_cannot_list_organizations(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="regular-list-orgs@example.com",
            is_superuser=False,
        )

        response = client.get("/organizations/")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_list_organizations(self, client):
        response = client.get("/organizations/")
        assert response.status_code == 401
