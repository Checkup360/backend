from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Organization
from app.persistence.models.organization import Organization as OrganizationORM
from app.persistence.models.membership import Membership
from app.persistence.repositories.base import BaseRepository
from uuid import UUID


class OrganizationRepository(BaseRepository[OrganizationORM, Organization]):
    def __init__(self, db: AsyncSession):
        super().__init__(OrganizationORM, db)

    @property
    def _base_query(self):
        return (
            select(
                self.model, func.count(Membership.user_id).label("collaborators_count")
            )
            .outerjoin(Membership, Membership.organization_id == self.model.id)
            .group_by(self.model.id)
        )

    async def get(self, id: UUID) -> Organization | None:
        query = self._base_query.where(self.model.id == id)
        row = await self.db.execute(query)
        result = row.first()
        if not result:
            return None
        orm, count = result
        return self._to_domain(orm, count)

    async def get_by_slug(self, slug: str) -> Organization | None:
        query = self._base_query.where(self.model.slug == slug)
        row = await self.db.execute(query)
        result = row.first()
        if not result:
            return None
        orm, count = result
        return self._to_domain(orm, count)

    async def list(self) -> list[Organization]:
        result = await self.db.execute(self._base_query)
        return [self._to_domain(orm, count) for orm, count in result.all()]

    @staticmethod
    def _to_domain(orm: OrganizationORM, collaborators_count: int = 0) -> Organization:
        return Organization(
            id=orm.id,
            name=orm.name,
            slug=orm.slug,
            collaborators_count=collaborators_count,
        )

    def _from_domain(self, entity: Organization) -> dict:
        return {
            "id": entity.id,
            "name": entity.name,
            "slug": entity.slug,
        }
