import uuid

from app.domain.entities import MemberBiometrics
from app.domain.repositories import MemberBiometricsRepository


class MemberBiometricsService:
    def __init__(self, repo: MemberBiometricsRepository):
        self.repo = repo

    async def get_biometrics(self, user_id: uuid.UUID) -> MemberBiometrics | None:
        return await self.repo.get_by_user(user_id)

    async def update_biometrics(
        self,
        user_id: uuid.UUID,
        biological_sex: str | None = None,
        height: float | None = None,
        weight: float | None = None,
        waist_circumference: float | None = None,
        neck_circumference: float | None = None,
        snoring: bool | None = None,
        tired: bool | None = None,
        observed_apnea: bool | None = None,
        hypertension_medication: bool | None = None,
        daily_physical_activity: bool | None = None,
        fruits_vegetables: bool | None = None,
        previous_high_glucose: bool | None = None,
        family_diabetes: str | None = None,
    ) -> MemberBiometrics:
        existing = await self.repo.get_by_user(user_id)
        if existing is None:
            existing = MemberBiometrics(user_id=user_id)

        if biological_sex is not None:
            existing.biological_sex = biological_sex
        if height is not None:
            existing.height = height
        if weight is not None:
            existing.weight = weight
        if waist_circumference is not None:
            existing.waist_circumference = waist_circumference
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

        await self.repo.save(existing)
        return existing
