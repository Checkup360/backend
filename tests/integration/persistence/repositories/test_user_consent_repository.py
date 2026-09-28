from datetime import datetime, timezone
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user_consent import ConsentType, UserConsent
from app.infrastructure.persistence.models import User
from app.infrastructure.persistence.repositories.user_consent import (
    SQLAlchemyUserConsentRepository,
)


@pytest.mark.asyncio
async def test_user_consent_repository_crud_active_and_revocation(
    db: AsyncSession, make_user
):
    user: User = await make_user(email="consent_user@example.com")
    repo = SQLAlchemyUserConsentRepository(db)

    # 1. Save an active consent
    consent = UserConsent(
        id=uuid.uuid4(),
        user_id=user.id,
        consent_type=ConsentType.TERMS_AND_CONDITIONS,
        document_version="1.0.0",
        accepted_at=datetime.now(timezone.utc),
    )
    saved = await repo.save(consent)
    assert saved.id == consent.id
    assert saved.is_active is True

    # 2. Query active consent
    active = await repo.get_active_consent(
        user_id=user.id,
        consent_type=ConsentType.TERMS_AND_CONDITIONS,
    )
    assert active is not None
    assert active.id == consent.id
    assert active.document_version == "1.0.0"

    # 3. Form-specific consent
    form_consent = UserConsent(
        id=uuid.uuid4(),
        user_id=user.id,
        consent_type=ConsentType.FORM_CONSENT,
        form_type="biometrics",
        document_version="1",
        accepted_at=datetime.now(timezone.utc),
    )
    await repo.save(form_consent)

    active_form = await repo.get_active_consent(
        user_id=user.id,
        consent_type=ConsentType.FORM_CONSENT,
        form_type="biometrics",
    )
    assert active_form is not None
    assert active_form.form_type == "biometrics"

    # Check non-existent active form consent
    no_sleep = await repo.get_active_consent(
        user_id=user.id,
        consent_type=ConsentType.FORM_CONSENT,
        form_type="sleep",
    )
    assert no_sleep is None

    # 4. Revocation
    revocation_time = datetime.now(timezone.utc)
    revoked = await repo.revoke(form_consent.id, revocation_time)
    assert revoked is not None
    assert revoked.is_active is False
    assert revoked.revoked_at is not None

    # Now get_active_consent should return None for biometrics
    active_after_revoke = await repo.get_active_consent(
        user_id=user.id,
        consent_type=ConsentType.FORM_CONSENT,
        form_type="biometrics",
    )
    assert active_after_revoke is None

    # List all consents for user
    user_consents = await repo.list_by_user_id(user.id)
    assert len(user_consents) == 2
