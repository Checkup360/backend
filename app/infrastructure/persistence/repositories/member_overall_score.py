from datetime import datetime
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.member_overall_score import MemberOverallScore
from app.domain.repositories.member_overall_score import MemberOverallScoreRepository
from app.infrastructure.persistence.models.member_overall_score import (
    MemberOverallScoreModel,
)


class SQLAlchemyMemberOverallScoreRepository(MemberOverallScoreRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: MemberOverallScoreModel) -> MemberOverallScore:
        return MemberOverallScore(
            id=model.id,
            user_id=model.user_id,
            organization_id=model.organization_id,
            score_weights_id=model.score_weights_id,
            submission_id=model.submission_id,
            overall_score=model.overall_score,
            risk_level=model.risk_level,
            evaluated_at=model.evaluated_at,
        )

    def _to_model(self, entity: MemberOverallScore) -> MemberOverallScoreModel:
        return MemberOverallScoreModel(
            id=entity.id,
            user_id=entity.user_id,
            organization_id=entity.organization_id,
            score_weights_id=entity.score_weights_id,
            submission_id=entity.submission_id,
            overall_score=entity.overall_score,
            risk_level=entity.risk_level,
            evaluated_at=entity.evaluated_at,
        )

    async def save(
        self, member_overall_score: MemberOverallScore
    ) -> MemberOverallScore:
        model = self._to_model(member_overall_score)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_latest_by_user_id(
        self, user_id: uuid.UUID
    ) -> MemberOverallScore | None:
        stmt = (
            select(MemberOverallScoreModel)
            .where(MemberOverallScoreModel.user_id == user_id)
            .order_by(desc(MemberOverallScoreModel.evaluated_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_latest_by_user_ids(
        self, user_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, MemberOverallScore]:
        if not user_ids:
            return {}

        stmt = (
            select(MemberOverallScoreModel)
            .where(MemberOverallScoreModel.user_id.in_(user_ids))
            .order_by(
                MemberOverallScoreModel.user_id,
                desc(MemberOverallScoreModel.evaluated_at),
            )
        )
        result = await self.session.execute(stmt)
        latest_map: dict[uuid.UUID, MemberOverallScore] = {}
        for model in result.scalars().all():
            if model.user_id not in latest_map:
                latest_map[model.user_id] = self._to_entity(model)
        return latest_map

    async def get_history_by_user_id(
        self, user_id: uuid.UUID
    ) -> list[MemberOverallScore]:
        stmt = (
            select(MemberOverallScoreModel)
            .where(MemberOverallScoreModel.user_id == user_id)
            .order_by(desc(MemberOverallScoreModel.evaluated_at))
        )
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_history_by_organization_id(
        self, organization_id: uuid.UUID, since: datetime | None = None
    ) -> list[MemberOverallScore]:
        stmt = select(MemberOverallScoreModel).where(
            MemberOverallScoreModel.organization_id == organization_id
        )
        if since is not None:
            stmt = stmt.where(MemberOverallScoreModel.evaluated_at >= since)
        stmt = stmt.order_by(desc(MemberOverallScoreModel.evaluated_at))
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_submission_id(
        self, submission_id: uuid.UUID
    ) -> MemberOverallScore | None:
        stmt = (
            select(MemberOverallScoreModel)
            .where(MemberOverallScoreModel.submission_id == submission_id)
            .order_by(desc(MemberOverallScoreModel.evaluated_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
