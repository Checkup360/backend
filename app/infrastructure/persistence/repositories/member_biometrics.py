import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.domain.entities.member_biometrics import (
    MemberBiometrics as MemberBiometricsEntity,
)
from app.domain.repositories.member_biometrics import MemberBiometricsRepository
from app.infrastructure.persistence.models.member_biometrics import (
    MemberBiometrics as MemberBiometricsModel,
)
from app.infrastructure.persistence.repositories.base import BaseRepository


from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyMemberBiometricsRepository(BaseRepository, MemberBiometricsRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(MemberBiometricsModel, db)

    async def get_by_user(self, user_id: uuid.UUID) -> MemberBiometricsEntity | None:
        stmt = select(MemberBiometricsModel).where(
            MemberBiometricsModel.user_id == user_id
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None

        return self._to_entity(model)

    async def save(self, biometrics: MemberBiometricsEntity) -> None:
        values: dict[str, Any] = {
            "user_id": biometrics.user_id,
            "biological_sex": biometrics.biological_sex,
            "height": biometrics.height,
            "weight": biometrics.weight,
            "waist_circumference": biometrics.waist_circumference,
            "neck_circumference": biometrics.neck_circumference,
        }

        stmt = insert(MemberBiometricsModel).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "biological_sex": stmt.excluded.biological_sex,
                "height": stmt.excluded.height,
                "weight": stmt.excluded.weight,
                "waist_circumference": stmt.excluded.waist_circumference,
                "neck_circumference": stmt.excluded.neck_circumference,
            },
        )
        await self.db.execute(stmt)

    def _to_entity(self, model: MemberBiometricsModel) -> MemberBiometricsEntity:
        return MemberBiometricsEntity(
            user_id=model.user_id,
            biological_sex=model.biological_sex,
            height=model.height,
            weight=model.weight,
            waist_circumference=model.waist_circumference,
            neck_circumference=model.neck_circumference,
        )
