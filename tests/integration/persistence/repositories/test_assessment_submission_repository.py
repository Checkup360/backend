from datetime import datetime, timezone
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.assessment_submission import AssessmentSubmission
from app.domain.entities.user_consent import ConsentType, UserConsent
from app.infrastructure.persistence.models import Organization, User
from app.infrastructure.persistence.repositories.assessment_submission import (
    SQLAlchemyAssessmentSubmissionRepository,
)
from app.infrastructure.persistence.repositories.user_consent import (
    SQLAlchemyUserConsentRepository,
)


@pytest.mark.asyncio
async def test_assessment_submission_repository_with_consent_id(
    db: AsyncSession, make_user, make_organization
):
    user: User = await make_user(email="sub_user@example.com")
    org: Organization = await make_organization(name="Org Sub", slug="org-sub")

    consent_repo = SQLAlchemyUserConsentRepository(db)
    consent = UserConsent(
        id=uuid.uuid4(),
        user_id=user.id,
        consent_type=ConsentType.FORM_CONSENT,
        form_type="biometrics",
        document_version="1",
        accepted_at=datetime.now(timezone.utc),
    )
    saved_consent = await consent_repo.save(consent)

    sub_repo = SQLAlchemyAssessmentSubmissionRepository(db)
    submission = AssessmentSubmission(
        id=uuid.uuid4(),
        user_id=user.id,
        organization_id=org.id,
        form_type="biometrics",
        form_version="1",
        status="completed",
        submitted_at=datetime.now(timezone.utc),
        consent_id=saved_consent.id,
        height=180.0,
        weight=75.0,
    )
    saved_sub = await sub_repo.save(submission)
    assert saved_sub.id == submission.id
    assert saved_sub.consent_id == saved_consent.id
    assert saved_sub.height == 180.0

    retrieved = await sub_repo.get_by_id(submission.id)
    assert retrieved is not None
    assert retrieved.consent_id == saved_consent.id
