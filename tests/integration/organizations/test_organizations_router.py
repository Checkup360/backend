import uuid
import pytest

from app.domain.value_objects.org_role import OrgRole


class TestOrganizationsRouter:
    @pytest.mark.asyncio
    async def test_list_organizations_filters_search_and_pagination(
        self, client, make_organization, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="sysadmin-orgs-list@example.com",
            is_superuser=True,
        )

        await make_organization(name="Alpha Hospital", slug="alpha-hospital")
        await make_organization(name="Beta Clinic", slug="beta-clinic")

        # Search filter
        res_search = client.get("/organizations/?search=Alpha")
        assert res_search.status_code == 200
        assert len(res_search.json()) == 1
        assert res_search.json()[0]["slug"] == "alpha-hospital"

        # Status filter "pending" (0 collaborators)
        res_status = client.get("/organizations/?status=pending")
        assert res_status.status_code == 200
        assert any(o["slug"] == "alpha-hospital" for o in res_status.json())

        # Pagination
        res_page = client.get("/organizations/?page=1&page_size=1")
        assert res_page.status_code == 200
        assert len(res_page.json()) == 1

    @pytest.mark.asyncio
    async def test_create_organization_slug_conflict_and_invalid_name(
        self, client, make_organization, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="sysadmin-org-create-err@example.com",
            is_superuser=True,
        )
        await make_organization(slug="duplicate-slug")

        # 409 Duplicate slug
        res_dup = client.post(
            "/organizations/",
            json={"name": "Duplicate Slug", "slug": "duplicate-slug"},
        )
        assert res_dup.status_code == 409
        assert res_dup.json()["detail"] == "organization_slug_already_exists"

        # 400/422 Invalid empty name
        res_invalid = client.post(
            "/organizations/",
            json={"name": "   ", "slug": "invalid-name"},
        )
        assert res_invalid.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_get_organization_summary_not_found(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="sysadmin-summary-404@example.com",
            is_superuser=True,
        )

        res = client.get(f"/organizations/{uuid.uuid4()}/summary")
        assert res.status_code == 404
        assert res.json()["detail"] == "organization_not_found"

    @pytest.mark.asyncio
    async def test_delete_organization_not_found(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="sysadmin-del-404@example.com",
            is_superuser=True,
        )

        res = client.delete(f"/organizations/{uuid.uuid4()}")
        assert res.status_code == 404
        assert res.json()["detail"] == "organization_not_found"

    @pytest.mark.asyncio
    async def test_list_departments_with_search(
        self, client, make_department, db_session_maker, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="org-admin-depts-search@example.com",
            memberships=[("dept-search-org", OrgRole.ADMIN)],
        )
        async with db_session_maker() as session:
            from app.infrastructure.persistence.models import Organization
            from sqlalchemy import select

            org = await session.scalar(
                select(Organization).where(Organization.slug == "dept-search-org")
            )

        await make_department(
            organization_id=org.id, name="Cardiology", slug="cardiology"
        )
        await make_department(
            organization_id=org.id, name="Pediatrics", slug="pediatrics"
        )

        res = client.get(f"/organizations/{org.id}/departments?search=cardio")
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 1
        assert items[0]["name"] == "Cardiology"

    @pytest.mark.asyncio
    async def test_create_department_duplicate_slug_conflict(
        self, client, make_department, db_session_maker, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="org-admin-dept-dup@example.com",
            memberships=[("dept-dup-org", OrgRole.ADMIN)],
        )
        async with db_session_maker() as session:
            from app.infrastructure.persistence.models import Organization
            from sqlalchemy import select

            org = await session.scalar(
                select(Organization).where(Organization.slug == "dept-dup-org")
            )

        await make_department(
            organization_id=org.id, name="Radiology", slug="radiology"
        )

        res = client.post(
            f"/organizations/{org.id}/departments",
            json={"name": "Radiology"},
        )
        assert res.status_code == 409
        assert res.json()["detail"] == "department_slug_already_exists"

    @pytest.mark.asyncio
    async def test_delete_department_in_use_conflict(
        self,
        client,
        make_department,
        make_user,
        make_membership,
        db_session_maker,
        auth_scenario,
    ):
        await auth_scenario.register_and_login(
            email="org-admin-dept-in-use@example.com",
            memberships=[("dept-in-use-org", OrgRole.ADMIN)],
        )
        async with db_session_maker() as session:
            from app.infrastructure.persistence.models import Organization
            from sqlalchemy import select

            org = await session.scalar(
                select(Organization).where(Organization.slug == "dept-in-use-org")
            )

        dept = await make_department(
            organization_id=org.id, name="Laboratory", slug="laboratory"
        )
        emp_user = await make_user(email="lab-emp@example.com")
        await make_membership(
            user_id=emp_user.id,
            organization_id=org.id,
            role="member",
            department_id=dept.id,
        )

        res = client.delete(f"/organizations/{org.id}/departments/{dept.id}")
        assert res.status_code == 409
        assert res.json()["detail"] == "department_in_use"

    @pytest.mark.asyncio
    async def test_assign_employee_department_and_list_filters(
        self,
        client,
        make_department,
        make_user,
        make_membership,
        db_session_maker,
        auth_scenario,
    ):
        await auth_scenario.register_and_login(
            email="org-admin-assign-dept@example.com",
            memberships=[("assign-dept-org", OrgRole.ADMIN)],
        )
        async with db_session_maker() as session:
            from app.infrastructure.persistence.models import Organization
            from sqlalchemy import select

            org = await session.scalar(
                select(Organization).where(Organization.slug == "assign-dept-org")
            )

        dept1 = await make_department(
            organization_id=org.id, name="Dept One", slug="dept-one"
        )
        dept2 = await make_department(
            organization_id=org.id, name="Dept Two", slug="dept-two"
        )

        user = await make_user(email="staff@example.com")
        await make_membership(
            user_id=user.id,
            organization_id=org.id,
            role="member",
            department_id=dept1.id,
        )

        # Reassign to Dept Two
        res = client.patch(
            f"/organizations/{org.id}/employees/{user.id}/department",
            json={"department_id": str(dept2.id)},
        )
        assert res.status_code == 200
        assert res.json()["department"]["name"] == "Dept Two"

        # Filter list_organization_employees by department_id
        res_filter = client.get(
            f"/organizations/{org.id}/employees?department_id={dept2.id}"
        )
        assert res_filter.status_code == 200
        assert len(res_filter.json()) == 1

        # Filter list_organization_employees by search and status
        res_search = client.get(
            f"/organizations/{org.id}/employees?search=staff&status=onboarding"
        )
        assert res_search.status_code == 200
        assert len(res_search.json()) == 1

    @pytest.mark.asyncio
    async def test_get_and_update_organization_score_weights(
        self,
        client,
        db_session_maker,
        auth_scenario,
    ):
        await auth_scenario.register_and_login(
            email="org-admin-weights@example.com",
            memberships=[("weights-org", OrgRole.ADMIN)],
        )
        async with db_session_maker() as session:
            from app.infrastructure.persistence.models import Organization
            from sqlalchemy import select

            org = await session.scalar(
                select(Organization).where(Organization.slug == "weights-org")
            )

        # GET default weights
        res_get = client.get(f"/organizations/{org.id}/score-weights")
        assert res_get.status_code == 200
        assert res_get.json()["score_weights"] == {
            "diabetes": 34.0,
            "sleep_apnea": 33.0,
            "depression": 33.0,
        }

        # PUT update weights
        new_weights = {"diabetes": 70.0, "sleep_apnea": 30.0}
        res_put = client.put(
            f"/organizations/{org.id}/score-weights",
            json={"score_weights": new_weights},
        )
        assert res_put.status_code == 200
        assert res_put.json()["score_weights"] == new_weights

        # GET updated weights
        res_get_updated = client.get(f"/organizations/{org.id}/score-weights")
        assert res_get_updated.status_code == 200
        assert res_get_updated.json()["score_weights"] == new_weights

    @pytest.mark.asyncio
    async def test_score_weights_unauthorized_member(
        self,
        client,
        db_session_maker,
        auth_scenario,
    ):
        await auth_scenario.register_and_login(
            email="org-member-weights@example.com",
            memberships=[("weights-member-org", OrgRole.MEMBER)],
        )
        async with db_session_maker() as session:
            from app.infrastructure.persistence.models import Organization
            from sqlalchemy import select

            org = await session.scalar(
                select(Organization).where(Organization.slug == "weights-member-org")
            )

        # Non-admin gets 403
        res_get = client.get(f"/organizations/{org.id}/score-weights")
        assert res_get.status_code == 403

        res_put = client.put(
            f"/organizations/{org.id}/score-weights",
            json={"score_weights": {"diabetes": 60.0, "sleep_apnea": 40.0}},
        )
        assert res_put.status_code == 403
