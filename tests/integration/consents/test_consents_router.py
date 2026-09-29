import uuid
import pytest


class TestConsentsRouter:
    @pytest.mark.asyncio
    async def test_get_current_consents_unauthenticated(self, client):
        response = client.get("/consents/current")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_consents_empty_initially(self, client, auth_scenario):
        await auth_scenario.register_and_login(email="new_user_consent@example.com")
        response = client.get("/consents/current")
        assert response.status_code == 200
        data = response.json()
        assert data["terms_and_conditions"] is None
        assert data["privacy_policy"] is None
        assert data["health_data_processing"] is None
        assert data["form_consents"] == {}

    @pytest.mark.asyncio
    async def test_accept_level1_consents_flow(self, client, auth_scenario):
        await auth_scenario.register_and_login(email="level1_user@example.com")

        # 1. Accept Terms and Conditions
        tc_res = client.post(
            "/consents",
            json={
                "consent_type": "TERMS_AND_CONDITIONS",
                "document_version": "1.0",
                "document_hash": "tc_hash_abc",
            },
        )
        assert tc_res.status_code == 201
        tc_data = tc_res.json()
        assert tc_data["consent_type"] == "TERMS_AND_CONDITIONS"
        assert tc_data["document_version"] == "1.0"
        assert tc_data["document_hash"] == "tc_hash_abc"
        assert tc_data["revoked_at"] is None

        # 2. Accept Privacy Policy
        pp_res = client.post(
            "/consents",
            json={
                "consent_type": "PRIVACY_POLICY",
                "document_version": "1.0",
            },
        )
        assert pp_res.status_code == 201

        # 3. Accept Health Data Processing Consent
        hp_res = client.post(
            "/consents",
            json={
                "consent_type": "HEALTH_DATA_PROCESSING_CONSENT",
                "document_version": "1.0",
            },
        )
        assert hp_res.status_code == 201

        # 4. Verify in GET /consents/current
        curr_res = client.get("/consents/current")
        assert curr_res.status_code == 200
        curr_data = curr_res.json()
        assert curr_data["terms_and_conditions"] is not None
        assert (
            curr_data["terms_and_conditions"]["consent_type"] == "TERMS_AND_CONDITIONS"
        )
        assert curr_data["privacy_policy"] is not None
        assert curr_data["privacy_policy"]["consent_type"] == "PRIVACY_POLICY"
        assert curr_data["health_data_processing"] is not None
        assert (
            curr_data["health_data_processing"]["consent_type"]
            == "HEALTH_DATA_PROCESSING_CONSENT"
        )
        assert curr_data["form_consents"] == {}

    @pytest.mark.asyncio
    async def test_accept_form_consent_and_revoke_flow(self, client, auth_scenario):
        await auth_scenario.register_and_login(email="form_user_consent@example.com")

        # 1. Accept biometrics form consent
        res = client.post(
            "/consents",
            json={
                "consent_type": "FORM_CONSENT",
                "form_type": "biometrics",
                "document_version": "1",
            },
        )
        assert res.status_code == 201
        consent = res.json()
        consent_id = consent["id"]
        assert consent["form_type"] == "biometrics"

        # 2. Check active consents
        curr_res = client.get("/consents/current")
        curr_data = curr_res.json()
        assert "biometrics" in curr_data["form_consents"]
        assert curr_data["form_consents"]["biometrics"]["id"] == consent_id

        # 3. Revoke consent
        revoke_res = client.post(f"/consents/{consent_id}/revoke")
        assert revoke_res.status_code == 200
        revoked_data = revoke_res.json()
        assert revoked_data["revoked_at"] is not None

        # 4. Check active consents again (should be removed from active dict)
        curr_after_res = client.get("/consents/current")
        curr_after_data = curr_after_res.json()
        assert "biometrics" not in curr_after_data["form_consents"]

        # 5. Revoking again should return 409 Conflict
        second_revoke = client.post(f"/consents/{consent_id}/revoke")
        assert second_revoke.status_code == 409
        assert second_revoke.json()["detail"] == "Consent has already been revoked"

    @pytest.mark.asyncio
    async def test_accept_form_consent_validation_errors(self, client, auth_scenario):
        await auth_scenario.register_and_login(email="validation_consent@example.com")

        # Missing form_type
        res1 = client.post(
            "/consents",
            json={
                "consent_type": "FORM_CONSENT",
            },
        )
        assert res1.status_code == 400
        assert res1.json()["detail"] == "Form type is required for FORM_CONSENT"

        # Invalid form_type
        res2 = client.post(
            "/consents",
            json={
                "consent_type": "FORM_CONSENT",
                "form_type": "invalid_test_form",
            },
        )
        assert res2.status_code == 400
        assert res2.json()["detail"] == "Invalid form type"

        # Invalid consent_type
        res3 = client.post(
            "/consents",
            json={
                "consent_type": "UNKNOWN_CONSENT",
            },
        )
        assert res3.status_code == 400
        assert res3.json()["detail"] == "Invalid consent type"

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_and_other_user_consent(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(email="owner_user@example.com")
        res = client.post(
            "/consents",
            json={
                "consent_type": "FORM_CONSENT",
                "form_type": "mood",
            },
        )
        consent_id = res.json()["id"]

        # Log in as a different user
        client.cookies.clear()
        await auth_scenario.register_and_login(email="attacker_user@example.com")

        # Attempt to revoke other user's consent
        revoke_other = client.post(f"/consents/{consent_id}/revoke")
        assert revoke_other.status_code == 404

        # Non-existent UUID
        random_id = str(uuid.uuid4())
        revoke_random = client.post(f"/consents/{random_id}/revoke")
        assert revoke_random.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_fundamental_consent_forbidden(self, client, auth_scenario):
        await auth_scenario.register_and_login(email="fundamental_user@example.com")
        res = client.post(
            "/consents",
            json={
                "consent_type": "TERMS_AND_CONDITIONS",
            },
        )
        consent_id = res.json()["id"]

        revoke_res = client.post(f"/consents/{consent_id}/revoke")
        assert revoke_res.status_code == 400
        assert (
            revoke_res.json()["detail"]
            == "Fundamental platform terms and privacy policy cannot be revoked independently"
        )
