import uuid
from datetime import datetime

from app.domain.entities.assessment_submission import AssessmentSubmission
from app.domain.repositories.assessment_submission import AssessmentSubmissionRepository


class SaveAssessmentSubmissionUseCase:
    def __init__(self, repository: AssessmentSubmissionRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        form_type: str,
        answers: dict,
        submitted_at: datetime,
    ) -> AssessmentSubmission:
        normalized_answers = {
            "sex": answers.get("biological_sex", answers.get("sex")),
            **{key: value for key, value in answers.items() if key != "biological_sex"},
        }
        submission = AssessmentSubmission(
            id=uuid.uuid4(),
            user_id=user_id,
            organization_id=organization_id,
            form_type=form_type,
            form_version="1",
            status="completed",
            submitted_at=submitted_at,
            **normalized_answers,
        )
        return await self._repository.save(submission)
