import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.risk_score import RiskScore
from app.domain.repositories.risk_score import RiskScoreRepository
from app.infrastructure.persistence.models.risk_score import RiskScoreModel


class SQLAlchemyRiskScoreRepository(RiskScoreRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: RiskScoreModel) -> RiskScore:
        return RiskScore(
            id=model.id,
            user_id=model.user_id,
            score_name=model.score_name,
            risk_level=model.risk_level,
            raw_value=model.raw_value,
            normalized_value=model.normalized_value,
            explanation=model.explanation,
            contributing_factors=model.contributing_factors,
            evaluated_at=model.evaluated_at,
        )

    def _to_model(self, entity: RiskScore) -> RiskScoreModel:
        return RiskScoreModel(
            id=entity.id,
            user_id=entity.user_id,
            score_name=entity.score_name,
            risk_level=entity.risk_level,
            raw_value=entity.raw_value,
            normalized_value=entity.normalized_value,
            explanation=entity.explanation,
            contributing_factors=entity.contributing_factors,
            evaluated_at=entity.evaluated_at,
        )

    async def save(self, risk_score: RiskScore) -> RiskScore:
        model = self._to_model(risk_score)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[RiskScore]:
        stmt = (
            select(RiskScoreModel)
            .where(RiskScoreModel.user_id == user_id)
            .order_by(RiskScoreModel.evaluated_at.desc())
        )
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]
