from datetime import date, datetime, timezone
import uuid
import pytest

from app.application.use_cases.consents.accept_consent import AcceptConsentUseCase
from app.application.use_cases.consents.get_active_consents import (
    GetActiveConsentsUseCase,
)
from app.application.use_cases.consents.revoke_consent import RevokeConsentUseCase
from app.domain.entities.user_consent import ConsentType, UserConsent
from app.domain.exceptions import (
    CannotRevokeFundamentalConsentError,
    ConsentAlreadyRevokedError,
    ConsentNotFoundError,
    FormTypeRequiredError,
    InvalidConsentTypeError,
    InvalidFormTypeError,
)
from app.domain.repositories.user_consent import UserConsentRepository
from app.domain.services.form_registry import FormRegistry
from app.domain.services.time_provider import TimeProvider


class FakeTimeProvider(TimeProvider):
    def __init__(self, now: datetime | None = None):
        self._now = now or datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    def utcnow(self) -> datetime:
        return self._now

    def today(self) -> date:
        return self._now.date()

    def set_now(self, now: datetime) -> None:
        self._now = now


class FakeUserConsentRepository(UserConsentRepository):
    def __init__(self):
        self.consents: dict[uuid.UUID, UserConsent] = {}

    async def get_by_id(self, consent_id: uuid.UUID) -> UserConsent | None:
        return self.consents.get(consent_id)

    async def get_active_consent(
        self,
        user_id: uuid.UUID,
        consent_type: ConsentType,
        form_type: str | None = None,
    ) -> UserConsent | None:
        active = [
            c
            for c in self.consents.values()
            if c.user_id == user_id
            and c.consent_type == consent_type
            and c.form_type == form_type
            and c.is_active
        ]
        if not active:
            return None
        active.sort(key=lambda c: c.accepted_at, reverse=True)
        return active[0]

    async def list_by_user_id(self, user_id: uuid.UUID) -> list[UserConsent]:
        user_consents = [c for c in self.consents.values() if c.user_id == user_id]
        user_consents.sort(key=lambda c: c.accepted_at, reverse=True)
        return user_consents

    async def save(self, consent: UserConsent) -> UserConsent:
        self.consents[consent.id] = consent
        return consent

    async def revoke(
        self, consent_id: uuid.UUID, revoked_at: datetime
    ) -> UserConsent | None:
        consent = self.consents.get(consent_id)
        if consent is None:
            return None
        consent.revoked_at = revoked_at
        return consent


@pytest.mark.asyncio
async def test_accept_terms_and_conditions():
    repo = FakeUserConsentRepository()
    time_provider = FakeTimeProvider()
    form_registry = FormRegistry()
    use_case = AcceptConsentUseCase(repo, time_provider, form_registry)

    user_id = uuid.uuid4()
    dto = await use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.TERMS_AND_CONDITIONS,
        document_version="1.0",
        ip_address="192.168.1.1",
        user_agent="TestAgent/1.0",
    )

    assert dto.user_id == user_id
    assert dto.consent_type == "TERMS_AND_CONDITIONS"
    assert dto.form_type is None
    assert dto.document_version == "1.0"
    assert dto.ip_address == "192.168.1.1"
    assert dto.user_agent == "TestAgent/1.0"
    assert dto.revoked_at is None
    assert dto.accepted_at == time_provider.utcnow()


@pytest.mark.asyncio
async def test_accept_form_consent_valid():
    repo = FakeUserConsentRepository()
    time_provider = FakeTimeProvider()
    form_registry = FormRegistry()
    use_case = AcceptConsentUseCase(repo, time_provider, form_registry)

    user_id = uuid.uuid4()
    dto = await use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.FORM_CONSENT,
        form_type="biometrics",
    )

    assert dto.user_id == user_id
    assert dto.consent_type == "FORM_CONSENT"
    assert dto.form_type == "biometrics"
    assert dto.document_version == "1"


@pytest.mark.asyncio
async def test_accept_form_consent_missing_form_type():
    repo = FakeUserConsentRepository()
    time_provider = FakeTimeProvider()
    form_registry = FormRegistry()
    use_case = AcceptConsentUseCase(repo, time_provider, form_registry)

    user_id = uuid.uuid4()
    with pytest.raises(FormTypeRequiredError):
        await use_case.execute(
            user_id=user_id,
            consent_type=ConsentType.FORM_CONSENT,
            form_type=None,
        )


@pytest.mark.asyncio
async def test_accept_form_consent_invalid_form_type():
    repo = FakeUserConsentRepository()
    time_provider = FakeTimeProvider()
    form_registry = FormRegistry()
    use_case = AcceptConsentUseCase(repo, time_provider, form_registry)

    user_id = uuid.uuid4()
    with pytest.raises(InvalidFormTypeError):
        await use_case.execute(
            user_id=user_id,
            consent_type=ConsentType.FORM_CONSENT,
            form_type="non_existent_form",
        )


@pytest.mark.asyncio
async def test_accept_consent_invalid_consent_type():
    repo = FakeUserConsentRepository()
    time_provider = FakeTimeProvider()
    form_registry = FormRegistry()
    use_case = AcceptConsentUseCase(repo, time_provider, form_registry)

    user_id = uuid.uuid4()
    with pytest.raises(InvalidConsentTypeError):
        await use_case.execute(
            user_id=user_id,
            consent_type="INVALID_TYPE",
        )


@pytest.mark.asyncio
async def test_accept_consent_idempotency_same_version_and_hash():
    repo = FakeUserConsentRepository()
    time_provider = FakeTimeProvider()
    form_registry = FormRegistry()
    use_case = AcceptConsentUseCase(repo, time_provider, form_registry)

    user_id = uuid.uuid4()
    first = await use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.PRIVACY_POLICY,
        document_version="1.0",
        document_hash="hash123",
    )

    second = await use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.PRIVACY_POLICY,
        document_version="1.0",
        document_hash="hash123",
    )

    assert first.id == second.id
    assert len(repo.consents) == 1


@pytest.mark.asyncio
async def test_accept_new_version_preserves_older_version_history():
    repo = FakeUserConsentRepository()
    time_provider = FakeTimeProvider(
        datetime(2026, 9, 29, 10, 0, 0, tzinfo=timezone.utc)
    )
    form_registry = FormRegistry()
    use_case = AcceptConsentUseCase(repo, time_provider, form_registry)
    get_use_case = GetActiveConsentsUseCase(repo)

    user_id = uuid.uuid4()
    v1 = await use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.PRIVACY_POLICY,
        document_version="1.0",
    )

    time_provider.set_now(datetime(2026, 9, 29, 11, 0, 0, tzinfo=timezone.utc))
    v2 = await use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.PRIVACY_POLICY,
        document_version="2.0",
    )

    assert v1.id != v2.id
    # Both records exist in historical storage
    assert len(repo.consents) == 2

    v1_stored = repo.consents[v1.id]
    assert v1_stored.document_version == "1.0"
    assert (
        v1_stored.revoked_at is None
    )  # Remains historical record without false revocation

    v2_stored = repo.consents[v2.id]
    assert v2_stored.document_version == "2.0"
    assert v2_stored.revoked_at is None

    # Active consent query returns the latest active version (v2)
    active = await get_use_case.execute(user_id)
    assert active.privacy_policy is not None
    assert active.privacy_policy.id == v2.id
    assert active.privacy_policy.document_version == "2.0"


@pytest.mark.asyncio
async def test_get_active_consents():
    repo = FakeUserConsentRepository()
    time_provider = FakeTimeProvider()
    form_registry = FormRegistry()
    accept_use_case = AcceptConsentUseCase(repo, time_provider, form_registry)
    get_use_case = GetActiveConsentsUseCase(repo)

    user_id = uuid.uuid4()
    empty = await get_use_case.execute(user_id)
    assert empty.terms_and_conditions is None
    assert empty.privacy_policy is None
    assert empty.health_data_processing is None
    assert empty.form_consents == {}

    await accept_use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.TERMS_AND_CONDITIONS,
    )
    await accept_use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.PRIVACY_POLICY,
    )
    await accept_use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.HEALTH_DATA_PROCESSING_CONSENT,
    )
    await accept_use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.FORM_CONSENT,
        form_type="biometrics",
    )
    await accept_use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.FORM_CONSENT,
        form_type="mood",
    )

    active = await get_use_case.execute(user_id)
    assert active.terms_and_conditions is not None
    assert active.privacy_policy is not None
    assert active.health_data_processing is not None
    assert "biometrics" in active.form_consents
    assert "mood" in active.form_consents
    assert len(active.form_consents) == 2


@pytest.mark.asyncio
async def test_revoke_form_consent():
    repo = FakeUserConsentRepository()
    time_provider = FakeTimeProvider(
        datetime(2026, 9, 29, 10, 0, 0, tzinfo=timezone.utc)
    )
    form_registry = FormRegistry()
    accept_use_case = AcceptConsentUseCase(repo, time_provider, form_registry)
    revoke_use_case = RevokeConsentUseCase(repo, time_provider)
    get_use_case = GetActiveConsentsUseCase(repo)

    user_id = uuid.uuid4()
    consent = await accept_use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.FORM_CONSENT,
        form_type="sleep",
    )

    time_provider.set_now(datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc))
    revoked = await revoke_use_case.execute(user_id=user_id, consent_id=consent.id)

    assert revoked.id == consent.id
    assert revoked.revoked_at == datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    # Now verify active consents does not include sleep
    active = await get_use_case.execute(user_id)
    assert "sleep" not in active.form_consents


@pytest.mark.asyncio
async def test_revoke_consent_not_found():
    repo = FakeUserConsentRepository()
    time_provider = FakeTimeProvider()
    revoke_use_case = RevokeConsentUseCase(repo, time_provider)

    with pytest.raises(ConsentNotFoundError):
        await revoke_use_case.execute(user_id=uuid.uuid4(), consent_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_revoke_consent_already_revoked():
    repo = FakeUserConsentRepository()
    time_provider = FakeTimeProvider()
    form_registry = FormRegistry()
    accept_use_case = AcceptConsentUseCase(repo, time_provider, form_registry)
    revoke_use_case = RevokeConsentUseCase(repo, time_provider)

    user_id = uuid.uuid4()
    consent = await accept_use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.FORM_CONSENT,
        form_type="sleep",
    )

    await revoke_use_case.execute(user_id=user_id, consent_id=consent.id)

    with pytest.raises(ConsentAlreadyRevokedError):
        await revoke_use_case.execute(user_id=user_id, consent_id=consent.id)


@pytest.mark.asyncio
async def test_revoke_fundamental_consent_forbidden():
    repo = FakeUserConsentRepository()
    time_provider = FakeTimeProvider()
    form_registry = FormRegistry()
    accept_use_case = AcceptConsentUseCase(repo, time_provider, form_registry)
    revoke_use_case = RevokeConsentUseCase(repo, time_provider)

    user_id = uuid.uuid4()
    terms = await accept_use_case.execute(
        user_id=user_id,
        consent_type=ConsentType.TERMS_AND_CONDITIONS,
    )
    with pytest.raises(CannotRevokeFundamentalConsentError):
        await revoke_use_case.execute(user_id=user_id, consent_id=terms.id)
