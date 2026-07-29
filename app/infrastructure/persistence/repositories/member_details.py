import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import MemberDetails
from app.infrastructure.persistence.models.member_details import (
    MemberDetails as MemberDetailsORM,
)
from app.infrastructure.persistence.repositories.base import BaseRepository


class MemberDetailsRepository(BaseRepository[MemberDetailsORM, MemberDetails]):
    def __init__(self, db: AsyncSession):
        super().__init__(MemberDetailsORM, db)

    async def get_by_user(self, user_id: uuid.UUID) -> MemberDetails | None:
        orm = await self.db.get(self.model, user_id)
        if orm is None:
            return None
        return self._to_domain(orm)

    async def save(self, entity: MemberDetails) -> MemberDetails:
        data = self._from_domain(entity)
        orm = await self.db.get(self.model, data["user_id"])
        if orm is not None:
            orm.date_of_birth = data["date_of_birth"]
            orm.first_name = data["first_name"]
            orm.last_name = data["last_name"]
            orm.phone_number = data["phone_number"]
            await self.db.commit()
            await self.db.refresh(orm)
            return self._to_domain(orm)
        return await self.create(**data)

    async def exists_for_user(self, user_id: uuid.UUID) -> bool:
        return await self.db.get(self.model, user_id) is not None

    @staticmethod
    def _to_domain(orm: MemberDetailsORM) -> MemberDetails:
        return MemberDetails(
            user_id=orm.user_id,
            date_of_birth=orm.date_of_birth,
            first_name=orm.first_name,
            last_name=orm.last_name,
            phone_number=orm.phone_number,
        )

    def _from_domain(self, entity: MemberDetails) -> dict:
        return {
            "user_id": entity.user_id,
            "date_of_birth": entity.date_of_birth,
            "first_name": entity.first_name,
            "last_name": entity.last_name,
            "phone_number": entity.phone_number,
        }
