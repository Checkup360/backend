from datetime import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user_consent import ConsentType, UserConsent
from app.domain.repositories.user_consent import UserConsentRepository
from app.infrastructure.persistence.models.user_consent import UserConsentModel


class SQLAlchemyUserConsentRepository(UserConsentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: UserConsentModel) -> UserConsent:
        return UserConsent(
            id=model.id,
            user_id=model.user_id,
            consent_type=ConsentType(model.consent_type),
            form_type=model.form_type,
            document_id=model.document_id,
            document_version=model.document_version,
            document_hash=model.document_hash,
            accepted_at=model.accepted_at,
            revoked_at=model.revoked_at,
            ip_address=model.ip_address,
            user_agent=model.user_agent,
        )

    async def get_by_id(self, consent_id: uuid.UUID) -> UserConsent | None:
        model = await self._session.get(UserConsentModel, consent_id)
        return self._to_entity(model) if model else None

    async def get_active_consent(
        self,
        user_id: uuid.UUID,
        consent_type: ConsentType,
        form_type: str | None = None,
    ) -> UserConsent | None:
        query = (
            select(UserConsentModel)
            .where(
                UserConsentModel.user_id == user_id,
                UserConsentModel.consent_type == consent_type.value,
                UserConsentModel.form_type == form_type,
                UserConsentModel.revoked_at.is_(None),
            )
            .order_by(UserConsentModel.accepted_at.desc())
        )
        result = await self._session.execute(query)
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def list_by_user_id(self, user_id: uuid.UUID) -> list[UserConsent]:
        query = (
            select(UserConsentModel)
            .where(UserConsentModel.user_id == user_id)
            .order_by(UserConsentModel.accepted_at.desc())
        )
        result = await self._session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save(self, consent: UserConsent) -> UserConsent:
        model = await self._session.get(UserConsentModel, consent.id)
        if model is None:
            model = UserConsentModel(
                id=consent.id,
                user_id=consent.user_id,
                consent_type=consent.consent_type.value,
                form_type=consent.form_type,
                document_id=consent.document_id,
                document_version=consent.document_version,
                document_hash=consent.document_hash,
                accepted_at=consent.accepted_at,
                revoked_at=consent.revoked_at,
                ip_address=consent.ip_address,
                user_agent=consent.user_agent,
            )
            self._session.add(model)
        else:
            model.revoked_at = consent.revoked_at

        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def revoke(
        self, consent_id: uuid.UUID, revoked_at: datetime
    ) -> UserConsent | None:
        model = await self._session.get(UserConsentModel, consent_id)
        if model is None:
            return None
        model.revoked_at = revoked_at
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)
