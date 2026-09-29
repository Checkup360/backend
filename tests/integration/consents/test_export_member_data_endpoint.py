from unittest.mock import AsyncMock
import pytest

from app.domain.value_objects import OrgRole
from app.presentation.api.dependencies import get_risk_scoring_service
from app.presentation.main import app


class TestExportMemberDataEndpoint:
    @pytest.fixture(autouse=True)
    def mock_risk_scoring_service(self):
        mock_service = AsyncMock()
        mock_service.get_catalog.return_value = []
        app.dependency_overrides[get_risk_scoring_service] = lambda: mock_service
        yield mock_service
        app.dependency_overrides.pop(get_risk_scoring_service, None)

    @pytest.mark.asyncio
    async def test_export_unauthenticated(self, client):
        response = client.get("/members/me/export")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_member_data_success(self, client, auth_scenario):
        member_user = await auth_scenario.register_and_login(
            email="maria.gonzalez@example.com",
            memberships=[("acme-corp", OrgRole.MEMBER)],
        )

        # 1. Complete onboarding profile
        client.post(
            "/members/me/details",
            json={
                "first_name": "Maria",
                "last_name": "Gonzalez",
                "phone_number": "+54 11 4444-5555",
                "date_of_birth": "1990-01-01",
            },
        )

        # 2. Accept baseline consents
        client.post(
            "/consents",
            json={
                "consent_type": "TERMS_AND_CONDITIONS",
                "document_version": "1.0",
            },
        )
        client.post(
            "/consents",
            json={
                "consent_type": "PRIVACY_POLICY",
                "document_version": "1.0",
            },
        )
        client.post(
            "/consents",
            json={
                "consent_type": "HEALTH_DATA_PROCESSING_CONSENT",
                "document_version": "1.0",
            },
        )
        client.post(
            "/consents",
            json={
                "consent_type": "FORM_CONSENT",
                "form_type": "biometrics",
                "document_version": "1.0",
            },
        )

        # 3. Submit biometrics form
        form_res = client.put(
            "/members/me/forms/biometrics",
            json={
                "biological_sex": "F",
                "height": 165.0,
                "weight": 60.0,
                "neck_circumference": 33.0,
                "waist_circumference": 75.0,
            },
        )
        assert form_res.status_code == 200

        # 4. Call export endpoint
        export_res = client.get("/members/me/export")
        assert export_res.status_code == 200
        data = export_res.json()

        assert data["profile"]["email"] == member_user.email
        assert data["profile"]["first_name"] == "Maria"
        assert data["profile"]["last_name"] == "Gonzalez"
        assert data["profile"]["date_of_birth"] == "1990-01-01"
        assert data["profile"]["organization"] == "Acme Corp"
        assert len(data["consents"]) == 4
        assert any(c["type"] == "Terms and Conditions" for c in data["consents"])
        assert any("Form Consent" in c["type"] for c in data["consents"])
        assert data["health_measurements"] is not None
        assert data["health_measurements"]["height"] == 165.0
        assert data["health_measurements"]["weight"] == 60.0
        assert len(data["assessment_history"]) >= 1
        assert data["assessment_history"][0]["form_type"] == "biometrics"
        assert "Habeas Data" in data["compliance_notice"]

        # 5. Verify audit log was created and reflected in compliance summary
        me_res = client.get("/auth/me")
        org_id = me_res.json()["membership"]["organization_id"]

        # Log out member and log in as sysadmin to inspect org compliance dashboard
        client.cookies.clear()
        await auth_scenario.register_and_login(
            email="sysadmin@checkup360.com",
            is_superuser=True,
        )

        summary_res = client.get(f"/organizations/{org_id}/compliance-summary")
        assert summary_res.status_code == 200
        assert summary_res.json()["data_exported_count"] == 1

        logs_res = client.get(
            f"/organizations/{org_id}/audit-logs?action=DATA_EXPORTED"
        )
        assert logs_res.status_code == 200
        assert logs_res.json()["total"] == 1
        assert logs_res.json()["items"][0]["action"] == "DATA_EXPORTED"
        assert logs_res.json()["items"][0]["user_email"] == "maria.gonzalez@example.com"
