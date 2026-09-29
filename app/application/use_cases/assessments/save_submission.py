import uuid
from datetime import datetime

from app.domain.entities.assessment_submission import AssessmentSubmission
from app.domain.repositories.assessment_submission import AssessmentSubmissionRepository
from app.domain.services.form_registry import FormRegistry


class SaveAssessmentSubmissionUseCase:
    def __init__(
        self,
        repository: AssessmentSubmissionRepository,
        form_registry: FormRegistry | None = None,
    ) -> None:
        self._repository = repository
        self._form_registry = form_registry or FormRegistry()

    async def execute(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        form_type: str,
        answers: dict,
        submitted_at: datetime,
        consent_id: uuid.UUID | None = None,
    ) -> AssessmentSubmission:
        normalized_answers = {
            "sex": answers.get("biological_sex", answers.get("sex")),
            **{key: value for key, value in answers.items() if key != "biological_sex"},
        }
        form_version = self._form_registry.get_form_version(form_type)
        submission = AssessmentSubmission(
            id=uuid.uuid4(),
            user_id=user_id,
            organization_id=organization_id,
            form_type=form_type,
            form_version=form_version,
            status="completed",
            submitted_at=submitted_at,
            consent_id=consent_id,
            **normalized_answers,
        )
        return await self._repository.save(submission)
