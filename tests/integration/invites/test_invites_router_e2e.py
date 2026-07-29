import pytest
from fastapi_users.password import PasswordHelper
from app.domain.value_objects.org_role import OrgRole


class TestInvitesRouterE2E:
    @pytest.mark.asyncio
    async def test_sysadmin_create_org_invite_missing_org_id(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="sysadmin-missing-org-id@example.com",
            is_superuser=True,
        )

        res = client.post(
            "/invites/organization",
            json={"email": "some@example.com", "role": "member"},
        )
        assert res.status_code == 422
        assert res.json()["detail"] == "organization_id_required_for_sysadmin"

    @pytest.mark.asyncio
    async def test_get_invite_metadata(self, client, make_invite, make_organization):
        org = await make_organization(name="Meta Org", slug="meta-org")
        invite = await make_invite(
            email="meta@example.com",
            organization_id=org.id,
            role=OrgRole.ADMIN,
        )

        res = client.get(f"/invites/{invite.token}")
        assert res.status_code == 200
        data = res.json()
        assert data["organization_id"] == str(org.id)
        assert data["organization_name"] == "Meta Org"
        assert data["role"] == "admin"
        assert data["is_sysadmin"] is False

    @pytest.mark.asyncio
    async def test_prepare_google_registration(
        self, client, make_invite, make_organization
    ):
        org = await make_organization(slug="google-session-org")
        invite = await make_invite(
            email="goog@example.com",
            organization_id=org.id,
            role=OrgRole.MEMBER,
        )

        # Valid token
        res = client.post(f"/invites/{invite.token}/google-session")
        assert res.status_code == 200
        assert res.json()["ok"] is True
        assert "pending_invite" in res.cookies

        # Invalid token
        res_invalid = client.post("/invites/non-existent-token/google-session")
        assert res_invalid.status_code == 400
        assert res_invalid.json()["code"] == "invalid_invite"

    @pytest.mark.asyncio
    async def test_redeem_invite_validation_and_auth_errors(
        self, client, make_invite, db_session_maker
    ):
        invite = await make_invite(
            email="redeem-err@example.com",
        )

        # Missing email and password
        res_missing = client.post(
            f"/invites/{invite.token}/redeem",
            json={},
        )
        assert res_missing.status_code == 400
        assert "Email and password are required" in res_missing.json()["detail"]

        # Wrong email for single-user invite
        res_email_mismatch = client.post(
            f"/invites/{invite.token}/redeem",
            json={"email": "wrong@example.com", "password": "Password123!"},
        )
        assert res_email_mismatch.status_code == 400

        # Existing user with wrong password
        hashed = PasswordHelper().hash("CorrectPassword123!")
        async with db_session_maker() as session:
            from app.infrastructure.persistence.models import User
            import uuid

            session.add(
                User(
                    id=uuid.uuid4(),
                    email="existing-redeem@example.com",
                    hashed_password=hashed,
                    is_active=True,
                    is_superuser=False,
                    is_verified=True,
                )
            )
            await session.commit()

        existing_invite = await make_invite(email="existing-redeem@example.com")
        res_bad_pass = client.post(
            f"/invites/{existing_invite.token}/redeem",
            json={
                "email": "existing-redeem@example.com",
                "password": "WrongPassword123!",
            },
        )
        assert res_bad_pass.status_code == 400
        assert res_bad_pass.json()["detail"] == "LOGIN_BAD_CREDENTIALS"

        # New user with invalid password (violates password policy)
        new_invite = await make_invite(email="new-invalid-pass@example.com")
        res_invalid_pass = client.post(
            f"/invites/{new_invite.token}/redeem",
            json={"email": "new-invalid-pass@example.com", "password": "123"},
        )
        assert res_invalid_pass.status_code == 400
        assert res_invalid_pass.json()["detail"]["code"] == "REGISTER_INVALID_PASSWORD"

    @pytest.mark.asyncio
    async def test_delete_org_invites_empty_ids(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="org-admin-del-empty@example.com",
            memberships=[("del-empty-org", OrgRole.ADMIN)],
        )

        res = client.request(
            "DELETE",
            "/invites/organization",
            json={"ids": []},
        )
        assert res.status_code == 422
        assert res.json()["detail"] == "invite_ids_required"
