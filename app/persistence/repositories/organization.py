from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import get_db
from app.domain.entities import Organization
from app.persistence.models.organization import Organization as OrganizationORM
from app.persistence.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[OrganizationORM, Organization]):
    def __init__(self, db: AsyncSession):
        super().__init__(OrganizationORM, db)

    async def get_by_slug(self, slug: str) -> Organization | None:
        query = select(self.model).where(self.model.slug == slug)
        orm = await self.db.scalar(query)
        return self._to_domain(orm) if orm else None

    @staticmethod
    def _to_domain(orm: OrganizationORM) -> Organization:
        return Organization(
            id=orm.id,
            name=orm.name,
            slug=orm.slug,
        )

    def _from_domain(self, entity: Organization) -> dict:
        return {
            "id": entity.id,
            "name": entity.name,
            "slug": entity.slug,
        }


async def get_organization_repository(
    db: AsyncSession = Depends(get_db),
) -> OrganizationRepository:
    return OrganizationRepository(db)
