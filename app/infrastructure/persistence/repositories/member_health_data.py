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
            "triglycerides": health_data.triglycerides,
            "total_cholesterol": health_data.total_cholesterol,
            "hdl_cholesterol": health_data.hdl_cholesterol,
            "systolic_blood_pressure": health_data.systolic_blood_pressure,
            "diastolic_blood_pressure": health_data.diastolic_blood_pressure,
            "fasting_glucose": health_data.fasting_glucose,
            "glucose_lowering_medication": health_data.glucose_lowering_medication,
            "neck_circumference": health_data.neck_circumference,
            "snoring": health_data.snoring,
            "tired": health_data.tired,
            "observed_apnea": health_data.observed_apnea,
            "smoker": health_data.smoker,
            "hypertension_medication": health_data.hypertension_medication,
            "daily_physical_activity": health_data.daily_physical_activity,
            "fruits_vegetables": health_data.fruits_vegetables,
            "previous_high_glucose": health_data.previous_high_glucose,
            "family_diabetes": health_data.family_diabetes,
            "little_interest": health_data.little_interest,
            "feeling_down": health_data.feeling_down,
            "sleep_trouble": health_data.sleep_trouble,
            "tired_energy": health_data.tired_energy,
            "appetite": health_data.appetite,
            "feeling_bad": health_data.feeling_bad,
            "concentration": health_data.concentration,
            "psychomotor": health_data.psychomotor,
            "self_harm_thoughts": health_data.self_harm_thoughts,
            "eoss_physical_health_stage": health_data.eoss_physical_health_stage,
            "eoss_mental_health_stage": health_data.eoss_mental_health_stage,
            "eoss_functional_stage": health_data.eoss_functional_stage,
            "statins": health_data.statins,
            "lab_study_date": health_data.lab_study_date,
        }

        stmt = insert(MemberHealthDataModel).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "biological_sex": stmt.excluded.biological_sex,
                "height": stmt.excluded.height,
                "weight": stmt.excluded.weight,
                "waist_circumference": stmt.excluded.waist_circumference,
                "triglycerides": stmt.excluded.triglycerides,
                "total_cholesterol": stmt.excluded.total_cholesterol,
                "hdl_cholesterol": stmt.excluded.hdl_cholesterol,
                "systolic_blood_pressure": stmt.excluded.systolic_blood_pressure,
                "diastolic_blood_pressure": stmt.excluded.diastolic_blood_pressure,
                "fasting_glucose": stmt.excluded.fasting_glucose,
                "glucose_lowering_medication": stmt.excluded.glucose_lowering_medication,
                "neck_circumference": stmt.excluded.neck_circumference,
                "snoring": stmt.excluded.snoring,
                "tired": stmt.excluded.tired,
                "observed_apnea": stmt.excluded.observed_apnea,
                "smoker": stmt.excluded.smoker,
                "hypertension_medication": stmt.excluded.hypertension_medication,
                "daily_physical_activity": stmt.excluded.daily_physical_activity,
                "fruits_vegetables": stmt.excluded.fruits_vegetables,
                "previous_high_glucose": stmt.excluded.previous_high_glucose,
                "family_diabetes": stmt.excluded.family_diabetes,
                "little_interest": stmt.excluded.little_interest,
                "feeling_down": stmt.excluded.feeling_down,
                "sleep_trouble": stmt.excluded.sleep_trouble,
                "tired_energy": stmt.excluded.tired_energy,
                "appetite": stmt.excluded.appetite,
                "feeling_bad": stmt.excluded.feeling_bad,
                "concentration": stmt.excluded.concentration,
                "psychomotor": stmt.excluded.psychomotor,
                "self_harm_thoughts": stmt.excluded.self_harm_thoughts,
                "eoss_physical_health_stage": stmt.excluded.eoss_physical_health_stage,
                "eoss_mental_health_stage": stmt.excluded.eoss_mental_health_stage,
                "eoss_functional_stage": stmt.excluded.eoss_functional_stage,
                "statins": stmt.excluded.statins,
                "lab_study_date": stmt.excluded.lab_study_date,
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
            triglycerides=model.triglycerides,
            total_cholesterol=model.total_cholesterol,
            hdl_cholesterol=model.hdl_cholesterol,
            systolic_blood_pressure=model.systolic_blood_pressure,
            diastolic_blood_pressure=model.diastolic_blood_pressure,
            fasting_glucose=model.fasting_glucose,
            glucose_lowering_medication=model.glucose_lowering_medication,
            neck_circumference=model.neck_circumference,
            snoring=model.snoring,
            tired=model.tired,
            observed_apnea=model.observed_apnea,
            smoker=model.smoker,
            hypertension_medication=model.hypertension_medication,
            daily_physical_activity=model.daily_physical_activity,
            fruits_vegetables=model.fruits_vegetables,
            previous_high_glucose=model.previous_high_glucose,
            family_diabetes=model.family_diabetes,
            little_interest=model.little_interest,
            feeling_down=model.feeling_down,
            sleep_trouble=model.sleep_trouble,
            tired_energy=model.tired_energy,
            appetite=model.appetite,
            feeling_bad=model.feeling_bad,
            concentration=model.concentration,
            psychomotor=model.psychomotor,
            self_harm_thoughts=model.self_harm_thoughts,
            eoss_physical_health_stage=model.eoss_physical_health_stage,
            eoss_mental_health_stage=model.eoss_mental_health_stage,
            eoss_functional_stage=model.eoss_functional_stage,
            statins=model.statins,
            lab_study_date=model.lab_study_date,
        )
