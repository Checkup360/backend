import uuid
from typing import Protocol

from app.domain.entities.risk_score import RiskScore


class RiskScoreRepository(Protocol):
    async def save(self, risk_score: RiskScore) -> RiskScore: ...

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[RiskScore]: ...
