import uuid

from app.domain.entities.assessment_submission import AssessmentSubmission
from app.domain.entities.risk_score import RiskScore
from app.domain.repositories.assessment_submission import AssessmentSubmissionRepository
from app.domain.repositories.risk_score import RiskScoreRepository


class GetAssessmentSubmissionsUseCase:
    def __init__(
        self,
        submission_repository: AssessmentSubmissionRepository,
        risk_score_repository: RiskScoreRepository,
    ) -> None:
        self._submission_repository = submission_repository
        self._risk_score_repository = risk_score_repository

    async def list_for_user(
        self, user_id: uuid.UUID, page: int, limit: int
    ) -> tuple[list[AssessmentSubmission], int]:
        return await self._submission_repository.list_by_user(
            user_id, (page - 1) * limit, limit
        )

    async def list_for_employee(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int,
        limit: int,
    ) -> tuple[list[AssessmentSubmission], int]:
        return await self._submission_repository.list_by_organization_employee(
            organization_id, user_id, (page - 1) * limit, limit
        )

    async def get_detail(
        self, submission_id: uuid.UUID
    ) -> tuple[AssessmentSubmission, list[RiskScore]] | None:
        submission = await self._submission_repository.get_by_id(submission_id)
        if submission is None:
            return None
        scores = await self._risk_score_repository.get_by_submission_id(submission_id)
        return submission, scores
