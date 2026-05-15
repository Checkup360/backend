import uuid
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.membership import Membership
from app.repositories.base import BaseRepository


class MembershipRepository(BaseRepository[Membership]):
    def __init__(self, db: AsyncSession):
        super().__init__(Membership, db)

    async def get_by_user_and_org(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Membership | None:
        query = select(self.model).where(
            self.model.user_id == user_id,
            self.model.organization_id == organization_id,
        )
        return await self.db.scalar(query)


async def get_membership_repository(
    db: AsyncSession = Depends(get_db),
) -> MembershipRepository:
    return MembershipRepository(db)
