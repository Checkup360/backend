from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select

from app.domain.entities.user_consent import ConsentType
from app.infrastructure.persistence.models.assessment_submission import (
    AssessmentSubmissionModel,
)
from app.presentation.api.dependencies import (
    get_risk_scoring_service,
    get_submit_assessment_use_case,
)
from app.application.use_cases.assessments.submit_assessment import (
    SubmitAssessmentUseCase,
)
from app.application.dto.risk_scoring import ScoreResultDTO
from app.presentation.main import app


class TestConsentEnforcement:
    @pytest.fixture(autouse=True)
    def mock_risk_scoring_service(self):
        mock_service = AsyncMock()
        mock_service.get_catalog.return_value = []
        mock_service.calculate.return_value = []
        app.dependency_overrides[get_risk_scoring_service] = lambda: mock_service
        yield mock_service
        app.dependency_overrides.pop(get_risk_scoring_service, None)

    @pytest.mark.asyncio
    async def test_form_submission_blocked_without_any_consent(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(email="no_consent_user@example.com")

        res = client.put(
            "/members/me/forms/biometrics",
            json={"biological_sex": "M", "height": 180.0, "weight": 75.0},
        )
        assert res.status_code == 403
        assert res.json()["detail"] == "health_data_processing_consent_required"

    @pytest.mark.asyncio
    async def test_form_submission_blocked_without_form_specific_consent(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="health_only_consent_user@example.com"
        )

        # Accept Level 1 Health Data Processing
        client.post(
            "/consents",
            json={"consent_type": ConsentType.HEALTH_DATA_PROCESSING_CONSENT.value},
        )

        # Attempt to submit mood form without mood form consent
        res = client.put(
            "/members/me/forms/mood",
            json={"feeling_down": 2, "little_interest": 1},
        )
        assert res.status_code == 403
        assert res.json()["detail"] == "active_consent_required_for_form_mood"

    @pytest.mark.asyncio
    async def test_form_submission_succeeds_with_consents_and_links_consent_id(
        self, client, auth_scenario, db_session_maker
    ):
        user = await auth_scenario.register_and_login(
            email="consented_form_user@example.com",
            memberships=[("acme-corp", "member")],
        )

        # 1. Accept Level 1 Health Data Processing
        client.post(
            "/consents",
            json={"consent_type": ConsentType.HEALTH_DATA_PROCESSING_CONSENT.value},
        )

        # 2. Accept Level 2 Form Consent for biometrics
        consent_res = client.post(
            "/consents",
            json={
                "consent_type": ConsentType.FORM_CONSENT.value,
                "form_type": "biometrics",
                "document_version": "1",
            },
        )
        assert consent_res.status_code == 201
        form_consent_id = consent_res.json()["id"]

        # 3. Submit biometrics form
        put_res = client.put(
            "/members/me/forms/biometrics",
            json={"biological_sex": "M", "height": 185.0, "weight": 80.0},
        )
        assert put_res.status_code == 200
        assert put_res.json()["status"] == "success"

        # 4. Verify assessment_submissions record is linked to form_consent_id
        async with db_session_maker() as session:
            sub = await session.scalar(
                select(AssessmentSubmissionModel)
                .where(
                    AssessmentSubmissionModel.user_id == user.id,
                    AssessmentSubmissionModel.form_type == "biometrics",
                )
                .order_by(AssessmentSubmissionModel.submitted_at.desc())
            )
            assert sub is not None
            assert str(sub.consent_id) == form_consent_id

    @pytest.mark.asyncio
    async def test_form_submission_blocked_after_consent_revocation(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="revoked_form_user@example.com",
            memberships=[("acme-corp", "member")],
        )

        # Accept Level 1
        client.post(
            "/consents",
            json={"consent_type": ConsentType.HEALTH_DATA_PROCESSING_CONSENT.value},
        )

        # Accept Level 2
        consent_res = client.post(
            "/consents",
            json={
                "consent_type": ConsentType.FORM_CONSENT.value,
                "form_type": "sleep",
            },
        )
        consent_id = consent_res.json()["id"]

        # First submission works
        res1 = client.put(
            "/members/me/forms/sleep",
            json={"snoring": True, "tired": True},
        )
        assert res1.status_code == 200

        # Revoke consent
        rev_res = client.post(f"/consents/{consent_id}/revoke")
        assert rev_res.status_code == 200

        # Subsequent submission is rejected
        res2 = client.put(
            "/members/me/forms/sleep",
            json={"snoring": False, "tired": False},
        )
        assert res2.status_code == 403
        assert res2.json()["detail"] == "active_consent_required_for_form_sleep"

    @pytest.mark.asyncio
    async def test_biometrics_patch_enforces_consent(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="biometrics_patch_user@example.com"
        )

        # 1. Blocked without consent
        res1 = client.patch(
            "/members/me/biometrics",
            json={"biological_sex": "F", "height": 165.0, "weight": 60.0},
        )
        assert res1.status_code == 403

        # 2. Accept Health Data Processing + Biometrics Form Consent
        client.post(
            "/consents",
            json={"consent_type": ConsentType.HEALTH_DATA_PROCESSING_CONSENT.value},
        )
        client.post(
            "/consents",
            json={
                "consent_type": ConsentType.FORM_CONSENT.value,
                "form_type": "biometrics",
            },
        )

        # 3. Patch succeeds
        res2 = client.patch(
            "/members/me/biometrics",
            json={"biological_sex": "F", "height": 165.0, "weight": 60.0},
        )
        assert res2.status_code == 200
        assert res2.json()["biological_sex"] == "F"

    @pytest.mark.asyncio
    async def test_assessments_evaluate_enforces_health_data_consent(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="evaluate_consent_user@example.com",
            memberships=[("acme-corp", "member")],
        )

        eval_payload = {
            "age": 35,
            "sex": "M",
            "height": 180.0,
            "weight": 78.0,
            "waist_circumference": 85.0,
            "systolic_blood_pressure": 120.0,
            "diastolic_blood_pressure": 80.0,
            "total_cholesterol": 180.0,
            "hdl_cholesterol": 50.0,
            "fasting_glucose": 90.0,
            "smoker": False,
        }

        # 1. Blocked without health data processing consent
        res1 = client.post("/members/me/assessments/evaluate", json=eval_payload)
        assert res1.status_code == 403
        assert res1.json()["detail"] == "health_data_processing_consent_required"

        # 2. Accept health data processing consent
        client.post(
            "/consents",
            json={"consent_type": ConsentType.HEALTH_DATA_PROCESSING_CONSENT.value},
        )

        mock_use_case = AsyncMock(spec=SubmitAssessmentUseCase)
        mock_use_case.execute.return_value = [
            ScoreResultDTO(
                score_id="sb-1",
                score_name="Sleep Apnea",
                domain="clinical",
                status="completed",
                risk_level="High",
                explanation="High risk of sleep apnea",
            ),
        ]
        app.dependency_overrides[get_submit_assessment_use_case] = lambda: mock_use_case

        # 3. Evaluate succeeds
        res2 = client.post("/members/me/assessments/evaluate", json=eval_payload)
        app.dependency_overrides.pop(get_submit_assessment_use_case, None)
        assert res2.status_code == 200

    @pytest.mark.asyncio
    async def test_form_a_consent_does_not_enable_form_b(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="isolated_form_user@example.com",
            memberships=[("acme-corp", "member")],
        )

        # Accept Level 1
        client.post(
            "/consents",
            json={"consent_type": ConsentType.HEALTH_DATA_PROCESSING_CONSENT.value},
        )

        # Accept Form Consent ONLY for biometrics
        client.post(
            "/consents",
            json={
                "consent_type": ConsentType.FORM_CONSENT.value,
                "form_type": "biometrics",
                "document_version": "1",
            },
        )

        # Biometrics submission succeeds
        res_bio = client.put(
            "/members/me/forms/biometrics",
            json={"biological_sex": "M", "height": 178.0, "weight": 72.0},
        )
        assert res_bio.status_code == 200

        # Sleep submission is blocked (form A consent does not enable form B)
        res_sleep = client.put(
            "/members/me/forms/sleep",
            json={"snoring": True, "tired": False},
        )
        assert res_sleep.status_code == 403
        assert res_sleep.json()["detail"] == "active_consent_required_for_form_sleep"

    @pytest.mark.asyncio
    async def test_version_bump_requires_reconsent_only_for_bumped_form(
        self, client, auth_scenario
    ):
        from app.presentation.api.dependencies import get_form_registry
        from app.domain.services.form_registry import FormDefinition, FormRegistry

        await auth_scenario.register_and_login(
            email="bump_version_user@example.com",
            memberships=[("acme-corp", "member")],
        )

        # Accept Level 1
        client.post(
            "/consents",
            json={"consent_type": ConsentType.HEALTH_DATA_PROCESSING_CONSENT.value},
        )

        # Accept v1 for biometrics and v1 for sleep
        client.post(
            "/consents",
            json={
                "consent_type": ConsentType.FORM_CONSENT.value,
                "form_type": "biometrics",
                "document_version": "1",
            },
        )
        client.post(
            "/consents",
            json={
                "consent_type": ConsentType.FORM_CONSENT.value,
                "form_type": "sleep",
                "document_version": "1",
            },
        )

        # Both forms succeed with v1
        assert (
            client.put(
                "/members/me/forms/biometrics",
                json={"biological_sex": "M", "height": 180.0, "weight": 75.0},
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/members/me/forms/sleep",
                json={"snoring": True, "tired": False},
            ).status_code
            == 200
        )

        # Now simulate a version bump on biometrics from "1" -> "2"
        default_registry = FormRegistry()
        bumped_forms = [
            f
            if f.form_type != "biometrics"
            else FormDefinition(
                form_type="biometrics",
                fields=f.fields,
                version="2",
            )
            for f in default_registry._forms.values()
        ]
        bumped_registry = FormRegistry(forms=bumped_forms)
        app.dependency_overrides[get_form_registry] = lambda: bumped_registry

        try:
            # Biometrics is now blocked because user only consented to v1
            res_bumped = client.put(
                "/members/me/forms/biometrics",
                json={"biological_sex": "M", "height": 180.0, "weight": 75.0},
            )
            assert res_bumped.status_code == 403
            assert (
                res_bumped.json()["detail"]
                == "active_consent_required_for_form_biometrics"
            )

            # Sleep form (still on v1) remains completely unaffected and succeeds!
            res_unaffected = client.put(
                "/members/me/forms/sleep",
                json={"snoring": False, "tired": False},
            )
            assert res_unaffected.status_code == 200

            # Re-consent to biometrics v2
            reconsent_res = client.post(
                "/consents",
                json={
                    "consent_type": ConsentType.FORM_CONSENT.value,
                    "form_type": "biometrics",
                    "document_version": "2",
                },
            )
            assert reconsent_res.status_code == 201

            # Biometrics now succeeds again
            res_reconsent = client.put(
                "/members/me/forms/biometrics",
                json={"biological_sex": "M", "height": 180.0, "weight": 75.0},
            )
            assert res_reconsent.status_code == 200
        finally:
            app.dependency_overrides.pop(get_form_registry, None)

    @pytest.mark.asyncio
    async def test_unauthenticated_endpoints_return_401(self, client):
        client.cookies.clear()
        assert client.get("/consents/current").status_code == 401
        assert client.post("/consents", json={}).status_code == 401
        assert client.get("/members/me/export").status_code == 401
        assert client.put("/members/me/forms/biometrics", json={}).status_code == 401
