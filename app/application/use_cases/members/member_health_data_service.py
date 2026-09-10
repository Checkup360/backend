import uuid

from app.domain.entities import MemberHealthData
from app.domain.repositories import MemberHealthDataRepository


class MemberHealthDataService:
    def __init__(self, repo: MemberHealthDataRepository):
        self.repo = repo

    async def get_health_data(self, user_id: uuid.UUID) -> MemberHealthData | None:
        return await self.repo.get_by_user(user_id)

    async def update_health_data(
        self,
        user_id: uuid.UUID,
        biological_sex: str | None = None,
        height: float | None = None,
        weight: float | None = None,
        waist_circumference: float | None = None,
        triglycerides: float | None = None,
        hdl_cholesterol: float | None = None,
        systolic_blood_pressure: float | None = None,
        diastolic_blood_pressure: float | None = None,
        fasting_glucose: float | None = None,
        glucose_lowering_medication: bool | None = None,
        neck_circumference: float | None = None,
        snoring: bool | None = None,
        tired: bool | None = None,
        observed_apnea: bool | None = None,
        hypertension_medication: bool | None = None,
        daily_physical_activity: bool | None = None,
        fruits_vegetables: bool | None = None,
        previous_high_glucose: bool | None = None,
        family_diabetes: str | None = None,
        little_interest: int | None = None,
        feeling_down: int | None = None,
        sleep_trouble: int | None = None,
        tired_energy: int | None = None,
        appetite: int | None = None,
        feeling_bad: int | None = None,
        concentration: int | None = None,
        psychomotor: int | None = None,
        self_harm_thoughts: int | None = None,
        eoss_physical_health_stage: int | None = None,
        eoss_mental_health_stage: int | None = None,
        eoss_functional_stage: int | None = None,
    ) -> MemberHealthData:
        existing = await self.repo.get_by_user(user_id)
        if existing is None:
            existing = MemberHealthData(user_id=user_id)

        if biological_sex is not None:
            existing.biological_sex = biological_sex
        if height is not None:
            existing.height = height
        if weight is not None:
            existing.weight = weight
        if waist_circumference is not None:
            existing.waist_circumference = waist_circumference
        if triglycerides is not None:
            existing.triglycerides = triglycerides
        if hdl_cholesterol is not None:
            existing.hdl_cholesterol = hdl_cholesterol
        if systolic_blood_pressure is not None:
            existing.systolic_blood_pressure = systolic_blood_pressure
        if diastolic_blood_pressure is not None:
            existing.diastolic_blood_pressure = diastolic_blood_pressure
        if fasting_glucose is not None:
            existing.fasting_glucose = fasting_glucose
        if glucose_lowering_medication is not None:
            existing.glucose_lowering_medication = glucose_lowering_medication
        if neck_circumference is not None:
            existing.neck_circumference = neck_circumference
        if snoring is not None:
            existing.snoring = snoring
        if tired is not None:
            existing.tired = tired
        if observed_apnea is not None:
            existing.observed_apnea = observed_apnea
        if hypertension_medication is not None:
            existing.hypertension_medication = hypertension_medication
        if daily_physical_activity is not None:
            existing.daily_physical_activity = daily_physical_activity
        if fruits_vegetables is not None:
            existing.fruits_vegetables = fruits_vegetables
        if previous_high_glucose is not None:
            existing.previous_high_glucose = previous_high_glucose
        if family_diabetes is not None:
            existing.family_diabetes = family_diabetes
        if little_interest is not None:
            existing.little_interest = little_interest
        if feeling_down is not None:
            existing.feeling_down = feeling_down
        if sleep_trouble is not None:
            existing.sleep_trouble = sleep_trouble
        if tired_energy is not None:
            existing.tired_energy = tired_energy
        if appetite is not None:
            existing.appetite = appetite
        if feeling_bad is not None:
            existing.feeling_bad = feeling_bad
        if concentration is not None:
            existing.concentration = concentration
        if psychomotor is not None:
            existing.psychomotor = psychomotor
        if self_harm_thoughts is not None:
            existing.self_harm_thoughts = self_harm_thoughts
        if eoss_physical_health_stage is not None:
            existing.eoss_physical_health_stage = eoss_physical_health_stage
        if eoss_mental_health_stage is not None:
            existing.eoss_mental_health_stage = eoss_mental_health_stage
        if eoss_functional_stage is not None:
            existing.eoss_functional_stage = eoss_functional_stage

        await self.repo.save(existing)
        return existing
