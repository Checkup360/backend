import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.member_health_data import (
    MemberHealthData as MemberHealthDataEntity,
)
from app.domain.repositories.member_health_data import MemberHealthDataRepository
from app.infrastructure.persistence.models.member_health_data import (
    MemberHealthData as MemberHealthDataModel,
)
from app.infrastructure.persistence.repositories.base import BaseRepository


class SQLAlchemyMemberHealthDataRepository(BaseRepository, MemberHealthDataRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(MemberHealthDataModel, db)

    async def get_by_user(self, user_id: uuid.UUID) -> MemberHealthDataEntity | None:
        stmt = select(MemberHealthDataModel).where(
            MemberHealthDataModel.user_id == user_id
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None

        return self._to_entity(model)

    async def save(self, health_data: MemberHealthDataEntity) -> None:
        values: dict[str, Any] = {
            "user_id": health_data.user_id,
            "biological_sex": health_data.biological_sex,
            "height": health_data.height,
            "weight": health_data.weight,
            "waist_circumference": health_data.waist_circumference,
            "neck_circumference": health_data.neck_circumference,
            "snoring": health_data.snoring,
            "tired": health_data.tired,
            "observed_apnea": health_data.observed_apnea,
            "hypertension_medication": health_data.hypertension_medication,
            "daily_physical_activity": health_data.daily_physical_activity,
            "fruits_vegetables": health_data.fruits_vegetables,
            "previous_high_glucose": health_data.previous_high_glucose,
            "family_diabetes": health_data.family_diabetes,
        }

        stmt = insert(MemberHealthDataModel).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "biological_sex": stmt.excluded.biological_sex,
                "height": stmt.excluded.height,
                "weight": stmt.excluded.weight,
                "waist_circumference": stmt.excluded.waist_circumference,
                "neck_circumference": stmt.excluded.neck_circumference,
                "snoring": stmt.excluded.snoring,
                "tired": stmt.excluded.tired,
                "observed_apnea": stmt.excluded.observed_apnea,
                "hypertension_medication": stmt.excluded.hypertension_medication,
                "daily_physical_activity": stmt.excluded.daily_physical_activity,
                "fruits_vegetables": stmt.excluded.fruits_vegetables,
                "previous_high_glucose": stmt.excluded.previous_high_glucose,
                "family_diabetes": stmt.excluded.family_diabetes,
            },
        )
        await self.db.execute(stmt)
        await self.db.commit()

    def _to_entity(self, model: MemberHealthDataModel) -> MemberHealthDataEntity:
        return MemberHealthDataEntity(
            user_id=model.user_id,
            biological_sex=model.biological_sex,
            height=model.height,
            weight=model.weight,
            waist_circumference=model.waist_circumference,
            neck_circumference=model.neck_circumference,
            snoring=model.snoring,
            tired=model.tired,
            observed_apnea=model.observed_apnea,
            hypertension_medication=model.hypertension_medication,
            daily_physical_activity=model.daily_physical_activity,
            fruits_vegetables=model.fruits_vegetables,
            previous_high_glucose=model.previous_high_glucose,
            family_diabetes=model.family_diabetes,
        )
