import uuid

import pytest

from app.infrastructure.persistence.models import Organization


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
    async def test_superuser_can_list_organizations_includes_collaborators_count(
        self, client, make_organization, auth_scenario, make_user, make_membership
    ):
        await auth_scenario.register_and_login(
            email="superuser-list-orgs-collaborators@example.com",
            is_superuser=True,
        )
        org1 = await make_organization(name="Org 1", slug="org-1")
        await make_organization(name="Org 2", slug="org-2")

        user1 = await make_user()
        user2 = await make_user()

        await make_membership(user_id=user1.id, organization_id=org1.id)
        await make_membership(user_id=user2.id, organization_id=org1.id)

        response = client.get("/organizations/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        org1_data = next(o for o in data if o["slug"] == "org-1")
        assert org1_data.get("collaborators_count") == 2

        org2_data = next(o for o in data if o["slug"] == "org-2")
        assert org2_data.get("collaborators_count") == 0

    @pytest.mark.asyncio
    async def test_superuser_can_list_organizations_filter_by_status(
        self, client, make_organization, auth_scenario, make_user, make_membership
    ):
        await auth_scenario.register_and_login(
            email="superuser-list-orgs-filter@example.com",
            is_superuser=True,
        )
        org1 = await make_organization(name="Org 1", slug="org-1")
        await make_organization(name="Org 2", slug="org-2")

        user1 = await make_user()
        await make_membership(user_id=user1.id, organization_id=org1.id)

        # Filter by active status
        res_active = client.get("/organizations/?status=active")
        assert res_active.status_code == 200
        active_data = res_active.json()
        assert len(active_data) == 1
        assert active_data[0]["slug"] == "org-1"

        # Filter by pending status
        res_pending = client.get("/organizations/?status=pending")
        assert res_pending.status_code == 200
        pending_data = res_pending.json()
        assert len(pending_data) == 1
        assert pending_data[0]["slug"] == "org-2"

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

    @pytest.mark.asyncio
    async def test_superuser_can_delete_organization_and_memberships(
        self,
        client,
        make_organization,
        auth_scenario,
        make_user,
        make_membership,
        make_invite,
        db_session_maker,
    ):
        await auth_scenario.register_and_login(
            email="superuser-delete-org@example.com",
            is_superuser=True,
        )
        org = await make_organization(name="Org To Delete", slug="org-delete")
        user = await make_user()
        await make_membership(user_id=user.id, organization_id=org.id)
        await make_invite(email="pending@example.com", organization_id=org.id)

        response = client.delete(f"/organizations/{org.id}")
        assert response.status_code == 204

        async with db_session_maker() as session:
            from app.infrastructure.persistence.models import Organization, Membership
            from app.infrastructure.persistence.models.invite import InviteToken
            from sqlalchemy import select

            deleted_org = await session.get(Organization, org.id)
            assert deleted_org is None

            memberships = await session.scalars(
                select(Membership).where(Membership.organization_id == org.id)
            )
            assert len(memberships.all()) == 0

            invites = await session.scalars(
                select(InviteToken).where(InviteToken.organization_id == org.id)
            )
            assert len(invites.all()) == 0

    @pytest.mark.asyncio
    async def test_non_superuser_cannot_delete_organization(
        self, client, auth_scenario, make_organization
    ):
        await auth_scenario.register_and_login(
            email="regular-delete-org@example.com",
            is_superuser=False,
        )
        org = await make_organization(name="Org To Keep", slug="org-keep")

        response = client.delete(f"/organizations/{org.id}")
        assert response.status_code == 403
