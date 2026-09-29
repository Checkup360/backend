import uuid

from app.application.dto.consent import UserConsentDTO
from app.domain.entities.audit_log import AuditLog
from app.domain.entities.user_consent import ConsentType, UserConsent
from app.domain.exceptions import (
    CannotRevokeFundamentalConsentError,
    ConsentAlreadyRevokedError,
    ConsentNotFoundError,
)
from app.domain.repositories.audit_log import AuditLogRepository
from app.domain.repositories.membership import MembershipRepository
from app.domain.repositories.user_consent import UserConsentRepository
from app.domain.services.time_provider import TimeProvider


class RevokeConsentUseCase:
    """Use case to revoke a previously accepted consent."""

    def __init__(
        self,
        repository: UserConsentRepository,
        time_provider: TimeProvider,
        audit_log_repository: AuditLogRepository | None = None,
        membership_repository: MembershipRepository | None = None,
    ) -> None:
        self._repository = repository
        self._time_provider = time_provider
        self._audit_log_repository = audit_log_repository
        self._membership_repository = membership_repository

    async def execute(
        self,
        user_id: uuid.UUID,
        consent_id: uuid.UUID,
    ) -> UserConsentDTO:
        consent = await self._repository.get_by_id(consent_id)
        if consent is None or consent.user_id != user_id:
            raise ConsentNotFoundError()

        if consent.revoked_at is not None:
            raise ConsentAlreadyRevokedError()

        consent_type = consent.consent_type
        if isinstance(consent_type, str):
            try:
                consent_type = ConsentType(consent_type)
            except ValueError:
                pass

        if consent_type in (
            ConsentType.TERMS_AND_CONDITIONS,
            ConsentType.PRIVACY_POLICY,
        ):
            raise CannotRevokeFundamentalConsentError()

        now = self._time_provider.utcnow()
        revoked_consent = await self._repository.revoke(consent_id, now)
        if revoked_consent is None:
            raise ConsentNotFoundError()

        if self._audit_log_repository:
            org_id = None
            if self._membership_repository:
                membership = await self._membership_repository.get_by_user(user_id)
                if membership:
                    org_id = membership.organization_id

            audit_entry = AuditLog.create(
                action="CONSENT_REVOKED",
                resource_type="USER_CONSENT",
                user_id=user_id,
                organization_id=org_id,
                resource_id=str(revoked_consent.id),
                details={
                    "consent_type": consent_type.value
                    if isinstance(consent_type, ConsentType)
                    else str(consent_type),
                    "form_type": revoked_consent.form_type,
                    "document_version": revoked_consent.document_version,
                    "revoked_at": now.isoformat(),
                },
            )
            await self._audit_log_repository.log(audit_entry)

        return self._to_dto(revoked_consent)

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
