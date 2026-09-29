import uuid

from app.application.dto.consent import ActiveConsentsDTO, UserConsentDTO
from app.domain.entities.user_consent import ConsentType, UserConsent
from app.domain.repositories.user_consent import UserConsentRepository


class GetActiveConsentsUseCase:
    """Use case to retrieve all currently active consents for a user."""

    def __init__(self, repository: UserConsentRepository) -> None:
        self._repository = repository

    async def execute(self, user_id: uuid.UUID) -> ActiveConsentsDTO:
        consents = await self._repository.list_by_user_id(user_id)
        active_consents = [c for c in consents if c.is_active]

        terms_and_conditions: UserConsentDTO | None = None
        privacy_policy: UserConsentDTO | None = None
        health_data_processing: UserConsentDTO | None = None
        form_consents: dict[str, UserConsentDTO] = {}

        for consent in active_consents:
            consent_type = consent.consent_type
            if isinstance(consent_type, str):
                try:
                    consent_type = ConsentType(consent_type)
                except ValueError:
                    continue

            dto = self._to_dto(consent)

            if consent_type == ConsentType.TERMS_AND_CONDITIONS:
                if (
                    terms_and_conditions is None
                    or consent.accepted_at > terms_and_conditions.accepted_at
                ):
                    terms_and_conditions = dto
            elif consent_type == ConsentType.PRIVACY_POLICY:
                if (
                    privacy_policy is None
                    or consent.accepted_at > privacy_policy.accepted_at
                ):
                    privacy_policy = dto
            elif consent_type == ConsentType.HEALTH_DATA_PROCESSING_CONSENT:
                if (
                    health_data_processing is None
                    or consent.accepted_at > health_data_processing.accepted_at
                ):
                    health_data_processing = dto
            elif consent_type == ConsentType.FORM_CONSENT and consent.form_type:
                existing = form_consents.get(consent.form_type)
                if existing is None or consent.accepted_at > existing.accepted_at:
                    form_consents[consent.form_type] = dto

        return ActiveConsentsDTO(
            terms_and_conditions=terms_and_conditions,
            privacy_policy=privacy_policy,
            health_data_processing=health_data_processing,
            form_consents=form_consents,
        )

    @staticmethod
    def _to_dto(consent: UserConsent) -> UserConsentDTO:
        return UserConsentDTO(
            id=consent.id,
            user_id=consent.user_id,
            consent_type=consent.consent_type.value
            if isinstance(consent.consent_type, ConsentType)
            else str(consent.consent_type),
            form_type=consent.form_type,
            document_id=consent.document_id,
            document_version=consent.document_version,
            document_hash=consent.document_hash,
            accepted_at=consent.accepted_at,
            revoked_at=consent.revoked_at,
            ip_address=consent.ip_address,
            user_agent=consent.user_agent,
        )
