from datetime import datetime
from typing import Any
import uuid
from sqlalchemy import func, select
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
        await self._session.commit()
        await self._session.refresh(model)
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

    async def list_by_organization(
        self,
        organization_id: uuid.UUID,
        action: str | None = None,
        user_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        filters = [AuditLogModel.organization_id == organization_id]
        if action:
            filters.append(AuditLogModel.action == action)
        if user_id:
            filters.append(AuditLogModel.user_id == user_id)
        if from_date:
            filters.append(AuditLogModel.created_at >= from_date)
        if to_date:
            filters.append(AuditLogModel.created_at <= to_date)

        # Count total matches
        count_query = select(func.count()).select_from(AuditLogModel).where(*filters)
        total_res = await self._session.execute(count_query)
        total = total_res.scalar() or 0

        # Fetch page items
        items_query = (
            select(AuditLogModel)
            .where(*filters)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items_res = await self._session.execute(items_query)
        models = items_res.scalars().all()

        return [self._to_entity(m) for m in models], total

    async def list_all(
        self,
        action: str | None = None,
        organization_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        filters = []
        if organization_id:
            filters.append(AuditLogModel.organization_id == organization_id)
        if action:
            filters.append(AuditLogModel.action == action)
        if user_id:
            filters.append(AuditLogModel.user_id == user_id)
        if from_date:
            filters.append(AuditLogModel.created_at >= from_date)
        if to_date:
            filters.append(AuditLogModel.created_at <= to_date)

        count_query = (
            select(func.count()).select_from(AuditLogModel).where(*filters)
            if filters
            else select(func.count()).select_from(AuditLogModel)
        )
        total_res = await self._session.execute(count_query)
        total = total_res.scalar() or 0

        items_query = select(AuditLogModel)
        if filters:
            items_query = items_query.where(*filters)
        items_query = (
            items_query.order_by(AuditLogModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items_res = await self._session.execute(items_query)
        models = items_res.scalars().all()

        return [self._to_entity(m) for m in models], total

    async def get_compliance_stats(
        self,
        organization_id: uuid.UUID,
    ) -> dict[str, Any]:
        # Aggregate actions count
        actions_query = (
            select(AuditLogModel.action, func.count(AuditLogModel.id))
            .where(AuditLogModel.organization_id == organization_id)
            .group_by(AuditLogModel.action)
        )
        actions_res = await self._session.execute(actions_query)
        action_counts = dict(actions_res.all())

        # Count unique users audited
        unique_users_query = select(
            func.count(func.distinct(AuditLogModel.user_id))
        ).where(
            AuditLogModel.organization_id == organization_id,
            AuditLogModel.user_id.is_not(None),
        )
        unique_users_res = await self._session.execute(unique_users_query)
        unique_users = unique_users_res.scalar() or 0

        return {
            "total_audit_events": sum(action_counts.values()),
            "consent_accepted_count": action_counts.get("CONSENT_ACCEPTED", 0),
            "consent_revoked_count": action_counts.get("CONSENT_REVOKED", 0),
            "data_exported_count": action_counts.get("DATA_EXPORTED", 0),
            "audited_members_count": unique_users,
            "actions_breakdown": action_counts,
        }
