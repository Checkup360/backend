from unittest.mock import AsyncMock
import pytest

from app.domain.value_objects import OrgRole
from app.presentation.api.dependencies import get_risk_scoring_service
from app.presentation.main import app


class TestAuditEndpoints:
    @pytest.fixture(autouse=True)
    def mock_risk_scoring_service(self):
        mock_service = AsyncMock()
        mock_service.get_catalog.return_value = []
        app.dependency_overrides[get_risk_scoring_service] = lambda: mock_service
        yield mock_service
        app.dependency_overrides.pop(get_risk_scoring_service, None)

    @pytest.mark.asyncio
    async def test_organization_audit_logs_flow(self, client, auth_scenario):
        # 1. Register and login as Org Admin
        await auth_scenario.register_and_login(
            email="admin@acme-corp.com",
            memberships=[("acme-corp", OrgRole.ADMIN)],
        )

        # Get organization id from auth me
        me_res = client.get("/auth/me")
        assert me_res.status_code == 200
        org_id = me_res.json()["membership"]["organization_id"]

        # Accept a consent as the admin user to generate an audit log
        consent_res = client.post(
            "/consents",
            json={
                "consent_type": "TERMS_AND_CONDITIONS",
                "document_version": "1.0",
            },
        )
        assert consent_res.status_code == 201

        # Query organization audit logs
        logs_res = client.get(f"/organizations/{org_id}/audit-logs")
        assert logs_res.status_code == 200
        logs_data = logs_res.json()
        assert logs_data["total"] >= 1
        assert any(
            log_item["action"] == "CONSENT_ACCEPTED" for log_item in logs_data["items"]
        )
        assert logs_data["items"][0]["user_email"] == "admin@acme-corp.com"

        # Query compliance summary
        summary_res = client.get(f"/organizations/{org_id}/compliance-summary")
        assert summary_res.status_code == 200
        summary_data = summary_res.json()
        assert summary_data["total_audit_events"] >= 1
        assert summary_data["consent_accepted_count"] >= 1

    @pytest.mark.asyncio
    async def test_system_audit_logs_flow(self, client, auth_scenario):
        # Register and login as sysadmin
        await auth_scenario.register_and_login(
            email="sysadmin@checkup360.com",
            is_superuser=True,
        )

        logs_res = client.get("/admin/audit-logs")
        assert logs_res.status_code == 200
        logs_data = logs_res.json()
        assert "items" in logs_data
        assert "total" in logs_data
