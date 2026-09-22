from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select

from app.domain.value_objects.org_role import OrgRole
from app.infrastructure.persistence.models import Organization, RefreshToken


async def _get_org(db_session_maker, slug: str) -> Organization:
    async with db_session_maker() as session:
        org = await session.scalar(
            select(Organization).where(Organization.slug == slug)
        )
        assert org is not None
        return org


def _switch_user(client, auth_scenario, email: str):
    client.cookies.clear()
    resp = auth_scenario.login(email)
    assert resp.status_code == 303


class TestSuperadminQuorum:
    @pytest.mark.asyncio
    async def test_cannot_request_removal_when_single_superadmin(
        self,
        client,
        db_session_maker,
        auth_scenario,
    ):
        sa = await auth_scenario.register_and_login(
            email="single-sa@example.com",
            memberships=[("single-sa-org", OrgRole.SUPERADMIN)],
        )
        org = await _get_org(db_session_maker, "single-sa-org")

        response = client.post(
            f"/organizations/{org.id}/superadmins/{sa.id}/removal-requests",
            json={"reason": "Should fail because only 1 superadmin"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_regular_admin_cannot_initiate_superadmin_removal(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="regular-admin-initiator@example.com",
            memberships=[("quorum-admin-org", OrgRole.ADMIN)],
        )
        org = await _get_org(db_session_maker, "quorum-admin-org")
        target_sa = await make_user(email="target-sa-for-admin@example.com")
        await make_membership(
            user_id=target_sa.id,
            organization_id=org.id,
            role="superadmin",
        )

        response = client.post(
            f"/organizations/{org.id}/superadmins/{target_sa.id}/removal-requests",
            json={"reason": "Admin trying to remove superadmin"},
        )
        assert response.status_code == 403

        # Also verify regular admin cannot list quorum removal requests
        list_resp = client.get(
            f"/organizations/{org.id}/superadmin-removal-requests",
        )
        assert list_resp.status_code == 403

    @pytest.mark.asyncio
    async def test_full_quorum_workflow_removes_superadmin_and_revokes_tokens(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_membership,
    ):
        # 1. Setup 3 superadmins
        sa1 = await auth_scenario.register_and_login(
            email="sa1@example.com",
            memberships=[("quorum-flow-org", OrgRole.SUPERADMIN)],
        )
        org = await _get_org(db_session_maker, "quorum-flow-org")

        client.cookies.clear()
        sa2 = await auth_scenario.register_and_login(email="sa2@example.com")
        await make_membership(
            user_id=sa2.id,
            organization_id=org.id,
            role="superadmin",
        )

        client.cookies.clear()
        sa3 = await auth_scenario.register_and_login(email="sa3@example.com")
        await make_membership(
            user_id=sa3.id,
            organization_id=org.id,
            role="superadmin",
        )

        # Give SA3 a refresh token to verify revocation
        async with db_session_maker() as session:
            session.add(
                RefreshToken(
                    user_id=sa3.id,
                    token_hash="fakehash-sa3-quorum",
                    expires_at=datetime.now(timezone.utc) + timedelta(days=1),
                )
            )
            await session.commit()

        # Log back in as SA1 to initiate request
        _switch_user(client, auth_scenario, "sa1@example.com")

        # 2. SA1 creates removal request for SA3
        req_resp = client.post(
            f"/organizations/{org.id}/superadmins/{sa3.id}/removal-requests",
            json={"reason": "Security protocol breach"},
        )
        assert req_resp.status_code == 201
        data = req_resp.json()
        request_id = data["id"]
        assert data["status"] == "pending"
        assert data["required_votes"] == 2  # 3 // 2 + 1 = 2
        assert len(data["votes"]) == 1
        assert data["votes"][0]["voter_user_id"] == str(sa1.id)
        assert data["votes"][0]["decision"] == "approve"

        # 3. Target SA3 cannot vote on their own removal
        _switch_user(client, auth_scenario, "sa3@example.com")
        self_vote_resp = client.post(
            f"/organizations/{org.id}/superadmin-removal-requests/{request_id}/votes",
            json={"decision": "reject"},
        )
        assert self_vote_resp.status_code == 403

        # 4. SA2 logs in and votes "approve"
        _switch_user(client, auth_scenario, "sa2@example.com")
        vote_resp = client.post(
            f"/organizations/{org.id}/superadmin-removal-requests/{request_id}/votes",
            json={"decision": "approve"},
        )
        assert vote_resp.status_code == 200
        vote_data = vote_resp.json()
        assert vote_data["status"] == "approved"
        assert len(vote_data["votes"]) == 2

        # 5. Verify SA3 lost superadmin role
        _switch_user(client, auth_scenario, "sa1@example.com")
        emp_resp = client.get(f"/organizations/{org.id}/employees")
        assert emp_resp.status_code == 200
        employees = emp_resp.json()
        sa3_emp = next(e for e in employees if e["id"] == str(sa3.id))
        assert "superadmin" not in sa3_emp["roles"]

        # 6. Verify SA3 refresh token was revoked
        async with db_session_maker() as session:
            tok = await session.scalar(
                select(RefreshToken).where(RefreshToken.user_id == sa3.id)
            )
            assert tok is not None
            assert tok.revoked_at is not None

    @pytest.mark.asyncio
    async def test_quorum_rejection_when_superadmin_votes_reject(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="sa-rej-1@example.com",
            memberships=[("quorum-rej-org", OrgRole.SUPERADMIN)],
        )
        org = await _get_org(db_session_maker, "quorum-rej-org")

        client.cookies.clear()
        sa2 = await auth_scenario.register_and_login(email="sa-rej-2@example.com")
        await make_membership(
            user_id=sa2.id,
            organization_id=org.id,
            role="superadmin",
        )

        client.cookies.clear()
        sa3 = await auth_scenario.register_and_login(email="sa-rej-3@example.com")
        await make_membership(
            user_id=sa3.id,
            organization_id=org.id,
            role="superadmin",
        )

        # SA1 requests removal of SA3
        _switch_user(client, auth_scenario, "sa-rej-1@example.com")
        req_resp = client.post(
            f"/organizations/{org.id}/superadmins/{sa3.id}/removal-requests",
            json={"reason": "Testing rejection flow"},
        )
        assert req_resp.status_code == 201
        request_id = req_resp.json()["id"]

        # SA2 votes reject
        _switch_user(client, auth_scenario, "sa-rej-2@example.com")
        vote_resp = client.post(
            f"/organizations/{org.id}/superadmin-removal-requests/{request_id}/votes",
            json={"decision": "reject"},
        )
        assert vote_resp.status_code == 200
        assert vote_resp.json()["status"] == "rejected"

        # Verify SA3 still has superadmin role
        _switch_user(client, auth_scenario, "sa-rej-1@example.com")
        emp_resp = client.get(f"/organizations/{org.id}/employees")
        assert emp_resp.status_code == 200
        employees = emp_resp.json()
        sa3_emp = next(e for e in employees if e["id"] == str(sa3.id))
        assert "superadmin" in sa3_emp["roles"]

        # Test status filtering and pagination
        active_resp = client.get(
            f"/organizations/{org.id}/superadmin-removal-requests?status=active",
        )
        assert active_resp.status_code == 200
        assert active_resp.json() == []

        inactive_resp = client.get(
            f"/organizations/{org.id}/superadmin-removal-requests?status=inactive",
        )
        assert inactive_resp.status_code == 200
        assert len(inactive_resp.json()) == 1
        assert inactive_resp.headers["X-Total-Count"] == "1"

        page_resp = client.get(
            f"/organizations/{org.id}/superadmin-removal-requests?page=1&page_size=1",
        )
        assert page_resp.status_code == 200
        assert len(page_resp.json()) == 1
        assert page_resp.headers["X-Page"] == "1"
        assert page_resp.headers["X-Page-Size"] == "1"
        assert page_resp.headers["X-Total-Count"] == "1"
