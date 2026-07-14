from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Organization
from app.infrastructure.persistence.models.organization import (
    Organization as OrganizationORM,
)
from app.infrastructure.persistence.models.membership import Membership
from app.infrastructure.persistence.repositories.base import BaseRepository
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
        return self._to_domain_with_count(orm, count)

    async def get_by_slug(self, slug: str) -> Organization | None:
        query = self._base_query.where(self.model.slug == slug)
        row = await self.db.execute(query)
        result = row.first()
        if not result:
            return None
        orm, count = result
        return self._to_domain_with_count(orm, count)

    async def delete(self, id: UUID) -> bool:
        from app.infrastructure.persistence.models.invite import InviteToken
        from app.infrastructure.persistence.models.department import Department

        await self.db.execute(
            delete(Membership).where(Membership.organization_id == id)
        )
        await self.db.execute(
            delete(InviteToken).where(InviteToken.organization_id == id)
        )
        await self.db.execute(
            delete(Department).where(Department.organization_id == id)
        )
        query = delete(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        await self.db.commit()
        return bool(getattr(result, "rowcount", 0) > 0)

    async def list(self) -> list[Organization]:
        result = await self.db.execute(self._base_query)
        return [self._to_domain_with_count(orm, count) for orm, count in result.all()]

    @staticmethod
    def _to_domain(orm: OrganizationORM) -> Organization:
        return OrganizationRepository._to_domain_with_count(orm, 0)

    @staticmethod
    def _to_domain_with_count(
        orm: OrganizationORM, collaborators_count: int
    ) -> Organization:
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
