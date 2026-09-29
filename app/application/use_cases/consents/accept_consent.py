import uuid

from app.application.dto.consent import UserConsentDTO
from app.domain.entities.audit_log import AuditLog
from app.domain.entities.user_consent import ConsentType, UserConsent
from app.domain.exceptions import (
    FormTypeRequiredError,
    InvalidConsentTypeError,
    InvalidFormTypeError,
)
from app.domain.repositories.audit_log import AuditLogRepository
from app.domain.repositories.membership import MembershipRepository
from app.domain.repositories.user_consent import UserConsentRepository
from app.domain.services.form_registry import FormRegistry
from app.domain.services.time_provider import TimeProvider


class AcceptConsentUseCase:
    """Use case to record user acceptance of a legal document or health form consent."""

    def __init__(
        self,
        repository: UserConsentRepository,
        time_provider: TimeProvider,
        form_registry: FormRegistry | None = None,
        audit_log_repository: AuditLogRepository | None = None,
        membership_repository: MembershipRepository | None = None,
    ) -> None:
        self._repository = repository
        self._time_provider = time_provider
        self._form_registry = form_registry or FormRegistry()
        self._audit_log_repository = audit_log_repository
        self._membership_repository = membership_repository

    async def execute(
        self,
        user_id: uuid.UUID,
        consent_type: str | ConsentType,
        form_type: str | None = None,
        document_version: str | None = None,
        document_id: uuid.UUID | None = None,
        document_hash: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> UserConsentDTO:
        parsed_consent_type = self._parse_consent_type(consent_type)

        if parsed_consent_type == ConsentType.FORM_CONSENT:
            if not form_type:
                raise FormTypeRequiredError()
            if not self._form_registry.is_valid_form_type(form_type):
                raise InvalidFormTypeError()
            if not document_version:
                document_version = self._form_registry.get_form_version(form_type)
        else:
            form_type = None
            if not document_version:
                document_version = "1"

        now = self._time_provider.utcnow()

        # If an identical active consent already exists, return it idempotently
        existing_active = await self._repository.get_active_consent(
            user_id=user_id,
            consent_type=parsed_consent_type,
            form_type=form_type,
        )
        if (
            existing_active
            and existing_active.document_version == document_version
            and existing_active.document_hash == document_hash
        ):
            return self._to_dto(existing_active)

        consent = UserConsent(
            id=uuid.uuid4(),
            user_id=user_id,
            consent_type=parsed_consent_type,
            form_type=form_type,
            document_id=document_id,
            document_version=document_version,
            document_hash=document_hash,
            accepted_at=now,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        saved = await self._repository.save(consent)

        if self._audit_log_repository:
            org_id = None
            if self._membership_repository:
                membership = await self._membership_repository.get_by_user(user_id)
                if membership:
                    org_id = membership.organization_id

            audit_entry = AuditLog.create(
                action="CONSENT_ACCEPTED",
                resource_type="USER_CONSENT",
                user_id=user_id,
                organization_id=org_id,
                resource_id=str(saved.id),
                details={
                    "consent_type": parsed_consent_type.value,
                    "form_type": form_type,
                    "document_version": document_version,
                    "document_hash": document_hash,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
            )
            await self._audit_log_repository.log(audit_entry)

        return self._to_dto(saved)

    def _parse_consent_type(self, consent_type: str | ConsentType) -> ConsentType:
        if isinstance(consent_type, ConsentType):
            return consent_type
        try:
            return ConsentType(consent_type)
        except ValueError:
            raise InvalidConsentTypeError()

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
