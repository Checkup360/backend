from datetime import datetime, timezone
from unittest.mock import AsyncMock
import uuid
import pytest

from app.application.use_cases.members.export_member_data import (
    ExportMemberDataUseCase,
)
from app.domain.entities.assessment_submission import AssessmentSubmission
from app.domain.entities.audit_log import AuditLog
from app.domain.entities.member_details import MemberDetails
from app.domain.entities.member_health_data import MemberHealthData
from app.domain.entities.membership import Membership
from app.domain.entities.organization import Organization
from app.domain.entities.risk_score import RiskScore
from app.domain.entities.user import User
from app.domain.entities.user_consent import ConsentType, UserConsent
from app.domain.exceptions import UserNotFoundError
from app.domain.value_objects import OrgRole


class MockTimeProvider:
    def __init__(self, now: datetime | None = None) -> None:
        self.now = now or datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    def utcnow(self) -> datetime:
        return self.now


@pytest.mark.asyncio
async def test_export_member_data_success():
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    fixed_time = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    user = User(
        id=user_id,
        email="test@example.com",
        is_active=True,
        is_superuser=False,
    )
    details = MemberDetails(
        user_id=user_id,
        first_name="Facundo",
        last_name="Test",
        phone_number="+541112345678",
        date_of_birth="1995-05-15",
        avatar_url="https://example.com/avatar.png",
    )
    membership = Membership(
        user_id=user_id,
        organization_id=org_id,
        roles=[OrgRole.MEMBER],
    )
    organization = Organization(
        id=org_id,
        name="Acme Corp",
        slug="acme-corp",
    )
    consent = UserConsent(
        id=uuid.uuid4(),
        user_id=user_id,
        consent_type=ConsentType.TERMS_AND_CONDITIONS,
        form_type=None,
        document_version="1.0",
        accepted_at=fixed_time,
    )
    health_data = MemberHealthData(
        user_id=user_id,
        biological_sex="male",
        height=180.0,
        weight=80.0,
        systolic_blood_pressure=120,
        diastolic_blood_pressure=80,
    )
    submission = AssessmentSubmission(
        id=uuid.uuid4(),
        user_id=user_id,
        organization_id=org_id,
        form_type="biometrics",
        form_version="1.0",
        height=180.0,
        weight=80.0,
        status="completed",
        submitted_at=fixed_time,
        consent_id=consent.id,
    )
    risk_score = RiskScore(
        id=uuid.uuid4(),
        user_id=user_id,
        score_name="cardiovascular",
        raw_value=2.5,
        normalized_value=2.5,
        risk_level="low",
        explanation=None,
        contributing_factors={},
        attention_flags={},
        evaluated_at=fixed_time,
    )

    user_repo = AsyncMock()
    user_repo.get.return_value = user

    member_details_repo = AsyncMock()
    member_details_repo.get_by_user.return_value = details

    membership_repo = AsyncMock()
    membership_repo.get_by_user.return_value = membership

    org_repo = AsyncMock()
    org_repo.get.return_value = organization

    user_consent_repo = AsyncMock()
    user_consent_repo.list_by_user_id.return_value = [consent]

    member_health_repo = AsyncMock()
    member_health_repo.get_by_user.return_value = health_data

    submission_repo = AsyncMock()
    submission_repo.list_by_user.return_value = ([submission], 1)

    risk_score_repo = AsyncMock()
    risk_score_repo.get_by_user_id.return_value = [risk_score]

    audit_repo = AsyncMock()
    time_provider = MockTimeProvider(fixed_time)

    use_case = ExportMemberDataUseCase(
        user_repository=user_repo,
        member_details_repository=member_details_repo,
        membership_repository=membership_repo,
        organization_repository=org_repo,
        user_consent_repository=user_consent_repo,
        member_health_data_repository=member_health_repo,
        assessment_submission_repository=submission_repo,
        risk_score_repository=risk_score_repo,
        audit_log_repository=audit_repo,
        time_provider=time_provider,
    )

    result = await use_case.execute(
        user_id=user_id,
        ip_address="192.168.1.1",
        user_agent="TestBrowser/1.0",
    )

    assert result.user_id == user_id
    assert result.email == "test@example.com"
    assert result.first_name == "Facundo"
    assert result.organization_name == "Acme Corp"
    assert len(result.consents) == 1
    assert result.consents[0].consent_type == "TERMS_AND_CONDITIONS"
    assert result.health_data is not None
    assert result.health_data["height"] == 180.0
    assert len(result.assessment_submissions) == 1
    assert result.assessment_submissions[0]["form_type"] == "biometrics"
    assert len(result.risk_scores) == 1
    assert result.risk_scores[0]["score_name"] == "cardiovascular"

    # Verify audit log was recorded
    audit_repo.log.assert_called_once()
    logged_entry: AuditLog = audit_repo.log.call_args[0][0]
    assert logged_entry.action == "DATA_EXPORTED"
    assert logged_entry.user_id == user_id
    assert logged_entry.organization_id == org_id
    assert logged_entry.details["consents_count"] == 1
    assert logged_entry.details["ip_address"] == "192.168.1.1"


@pytest.mark.asyncio
async def test_export_member_data_user_not_found():
    user_repo = AsyncMock()
    user_repo.get.return_value = None

    use_case = ExportMemberDataUseCase(
        user_repository=user_repo,
        member_details_repository=AsyncMock(),
        membership_repository=AsyncMock(),
        organization_repository=AsyncMock(),
        user_consent_repository=AsyncMock(),
        member_health_data_repository=AsyncMock(),
        assessment_submission_repository=AsyncMock(),
        risk_score_repository=AsyncMock(),
        audit_log_repository=AsyncMock(),
        time_provider=MockTimeProvider(),
    )

    with pytest.raises(UserNotFoundError):
        await use_case.execute(user_id=uuid.uuid4())
