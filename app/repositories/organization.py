from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.organization import Organization
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, db: AsyncSession):
        super().__init__(Organization, db)

    async def get_by_slug(self, slug: str) -> Organization | None:
        query = select(self.model).where(self.model.slug == slug)
        return await self.db.scalar(query)


async def get_organization_repository(
    db: AsyncSession = Depends(get_db),
) -> OrganizationRepository:
    return OrganizationRepository(db)
