import uuid

from app.domain.entities.risk_score import RiskScore
from app.domain.repositories.risk_score import RiskScoreRepository


class GetAssessmentsUseCase:
    def __init__(self, risk_score_repository: RiskScoreRepository) -> None:
        self._risk_score_repository = risk_score_repository

    async def execute(self, user_id: uuid.UUID) -> list[RiskScore]:
        return await self._risk_score_repository.get_by_user_id(user_id)
