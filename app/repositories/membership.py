import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.entities import Membership
from app.domain.entities.org_role import OrgRole
from app.models.membership import Membership as MembershipORM
from app.repositories.base import BaseRepository


class MembershipRepository(BaseRepository[MembershipORM, Membership]):
    def __init__(self, db: AsyncSession):
        super().__init__(MembershipORM, db)

    async def get_by_user_and_org(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Membership | None:
        query = select(self.model).where(
            self.model.user_id == user_id,
            self.model.organization_id == organization_id,
        )
        orm = await self.db.scalar(query)
        return self._to_domain(orm) if orm else None

    async def is_admin_of_any(self, user_id: uuid.UUID) -> bool:
        query = select(self.model).where(
            self.model.user_id == user_id,
            self.model.role == OrgRole.ADMIN,
        )
        result = await self.db.execute(query)
        return result.first() is not None

    async def update_role(
        self, user_id: uuid.UUID, organization_id: uuid.UUID, role: OrgRole
    ) -> Membership:
        orm = await self.db.get(self.model, (user_id, organization_id))
        if orm is None:
            raise ValueError("membership_not_found")
        orm.role = role
        await self.db.commit()
        await self.db.refresh(orm)
        return self._to_domain(orm)

    @staticmethod
    def _to_domain(orm: MembershipORM) -> Membership:
        return Membership(
            user_id=orm.user_id,
            organization_id=orm.organization_id,
            role=orm.role,
        )


async def get_membership_repository(
    db: AsyncSession = Depends(get_db),
) -> MembershipRepository:
    return MembershipRepository(db)
