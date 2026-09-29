import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.audit_log import AuditLog
from app.domain.repositories.audit_log import AuditLogRepository
from app.infrastructure.persistence.models.audit_log import AuditLogModel


class SQLAlchemyAuditLogRepository(AuditLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: AuditLogModel) -> AuditLog:
        return AuditLog(
            id=model.id,
            user_id=model.user_id,
            organization_id=model.organization_id,
            action=model.action,
            resource_type=model.resource_type,
            resource_id=model.resource_id,
            details=model.details or {},
            created_at=model.created_at,
        )

    async def log(self, audit_log: AuditLog) -> AuditLog:
        model = AuditLogModel(
            id=audit_log.id,
            user_id=audit_log.user_id,
            organization_id=audit_log.organization_id,
            action=audit_log.action,
            resource_type=audit_log.resource_type,
            resource_id=audit_log.resource_id,
            details=audit_log.details,
            created_at=audit_log.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def get_by_user_id(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        query = (
            select(AuditLogModel)
            .where(AuditLogModel.user_id == user_id)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_organization_id(
        self,
        organization_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        query = (
            select(AuditLogModel)
            .where(AuditLogModel.organization_id == organization_id)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]
