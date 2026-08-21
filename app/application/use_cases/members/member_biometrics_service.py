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
    ) -> None:
        biometrics = MemberBiometrics(
            user_id=user_id,
            biological_sex=biological_sex,
            height=height,
            weight=weight,
            waist_circumference=waist_circumference,
            neck_circumference=neck_circumference,
        )
        await self.repo.save(biometrics)
