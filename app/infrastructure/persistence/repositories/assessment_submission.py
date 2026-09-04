import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.assessment_submission import AssessmentSubmission
from app.domain.repositories.assessment_submission import AssessmentSubmissionRepository
from app.infrastructure.persistence.models.assessment_submission import (
    AssessmentSubmissionModel,
)


class SQLAlchemyAssessmentSubmissionRepository(AssessmentSubmissionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_entity(model: AssessmentSubmissionModel) -> AssessmentSubmission:
        values = {
            column.name: getattr(model, column.name)
            for column in AssessmentSubmissionModel.__table__.columns
        }
        return AssessmentSubmission(**values)

    async def save(self, submission: AssessmentSubmission) -> AssessmentSubmission:
        model = AssessmentSubmissionModel(**vars(submission))
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update_status(self, submission_id: uuid.UUID, status: str) -> None:
        model = await self.session.get(AssessmentSubmissionModel, submission_id)
        if model is None:
            return
        model.status = status
        await self.session.commit()

    async def get_by_id(self, submission_id: uuid.UUID) -> AssessmentSubmission | None:
        model = await self.session.get(AssessmentSubmissionModel, submission_id)
        return self._to_entity(model) if model else None

    async def list_by_user(
        self, user_id: uuid.UUID, offset: int, limit: int
    ) -> tuple[list[AssessmentSubmission], int]:
        return await self._list(
            AssessmentSubmissionModel.user_id == user_id,
            offset=offset,
            limit=limit,
        )

    async def list_by_organization_employee(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        offset: int,
        limit: int,
    ) -> tuple[list[AssessmentSubmission], int]:
        return await self._list(
            AssessmentSubmissionModel.organization_id == organization_id,
            AssessmentSubmissionModel.user_id == user_id,
            offset=offset,
            limit=limit,
        )

    async def _list(self, *conditions, offset: int, limit: int):
        base = select(AssessmentSubmissionModel).where(*conditions)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        result = await self.session.execute(
            base.order_by(AssessmentSubmissionModel.submitted_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [self._to_entity(model) for model in result.scalars()], int(total or 0)
