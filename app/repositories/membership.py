import uuid
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.membership import Membership, OrgRole
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

    async def is_admin_of_any(self, user_id: uuid.UUID) -> bool:
        query = select(self.model).where(
            self.model.user_id == user_id, self.model.role == OrgRole.ADMIN
        )
        result = await self.db.execute(query)
        return result.first() is not None


async def get_membership_repository(
    db: AsyncSession = Depends(get_db),
) -> MembershipRepository:
    return MembershipRepository(db)
