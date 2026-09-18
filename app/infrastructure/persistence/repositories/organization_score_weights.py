import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.organization_score_weights import OrganizationScoreWeights
from app.infrastructure.persistence.models.organization_score_weights import (
    OrganizationScoreWeightsModel,
)
from app.infrastructure.persistence.repositories.base import BaseRepository


class OrganizationScoreWeightsRepository(
    BaseRepository[OrganizationScoreWeightsModel, OrganizationScoreWeights]
):
    def __init__(self, db: AsyncSession):
        super().__init__(OrganizationScoreWeightsModel, db)

    async def save(self, entity: OrganizationScoreWeights) -> OrganizationScoreWeights:
        data = self._from_domain(entity)
        orm = await self.create(**data)
        return self._to_domain(orm)

    async def get_active_for_organization(
        self, organization_id: uuid.UUID
    ) -> OrganizationScoreWeights | None:
        query = (
            select(self.model)
            .where(self.model.organization_id == organization_id)
            .order_by(desc(self.model.version))
            .limit(1)
        )
        result = await self.db.execute(query)
        orm = result.scalars().first()
        return self._to_domain(orm) if orm else None

    async def get_by_id(self, id: uuid.UUID) -> OrganizationScoreWeights | None:
        return await self.get(id)

    async def list_versions_for_organization(
        self, organization_id: uuid.UUID
    ) -> list[OrganizationScoreWeights]:
        query = (
            select(self.model)
            .where(self.model.organization_id == organization_id)
            .order_by(desc(self.model.version))
        )
        result = await self.db.execute(query)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    def _to_domain(
        self, orm: OrganizationScoreWeightsModel
    ) -> OrganizationScoreWeights:
        return OrganizationScoreWeights(
            id=orm.id,
            organization_id=orm.organization_id,
            version=orm.version,
            weights=dict(orm.weights) if orm.weights else {},
            changed_by_user_id=orm.changed_by_user_id,
            created_at=orm.created_at,
        )

    def _from_domain(self, entity: OrganizationScoreWeights) -> dict:
        return {
            "id": entity.id,
            "organization_id": entity.organization_id,
            "version": entity.version,
            "weights": entity.weights,
            "changed_by_user_id": entity.changed_by_user_id,
            "created_at": entity.created_at,
        }
