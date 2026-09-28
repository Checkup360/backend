import uuid
from dataclasses import replace

from app.application.dto.risk_scoring import HealthDataDTO, ScoreResultDTO
from app.application.interfaces.risk_scoring_service import RiskScoringService
from app.domain.repositories.member_details import MemberDetailsRepository
from app.domain.repositories.risk_score import RiskScoreRepository
from app.domain.repositories.assessment_submission import AssessmentSubmissionRepository
from app.domain.entities.assessment_submission import AssessmentSubmission
from app.domain.entities.risk_score import RiskScore
from app.domain.services.form_registry import FormRegistry
from app.domain.services.time_provider import TimeProvider


class SubmitAssessmentUseCase:
    def __init__(
        self,
        risk_scoring_service: RiskScoringService,
        member_details_repository: MemberDetailsRepository,
        risk_score_repository: RiskScoreRepository,
        time_provider: TimeProvider,
        assessment_submission_repository: AssessmentSubmissionRepository | None = None,
        form_registry: FormRegistry | None = None,
    ) -> None:
        self._risk_scoring_service = risk_scoring_service
        self._member_details_repository = member_details_repository
        self._risk_score_repository = risk_score_repository
        self._time_provider = time_provider
        self._assessment_submission_repository = assessment_submission_repository
        self._form_registry = form_registry or FormRegistry()

    async def execute(
        self,
        user_id: uuid.UUID,
        health_data: HealthDataDTO,
        target_scores: list[str] | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> list[ScoreResultDTO]:
        # Retrieve member details to supplement the health data
        member_details = await self._member_details_repository.get_by_user(user_id)
        if not member_details:
            raise ValueError("Member details not found. Please complete onboarding.")

        # Calculate age
        today = self._time_provider.today()
        dob = member_details.date_of_birth
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        supplemented_data = replace(health_data, age=age)

        now = self._time_provider.utcnow()
        submission_id: uuid.UUID | None = None
        if self._assessment_submission_repository and organization_id:
            form_version = self._form_registry.get_form_version("clinical_assessment")
            submission = AssessmentSubmission(
                id=uuid.uuid4(),
                user_id=user_id,
                organization_id=organization_id,
                form_type="clinical_assessment",
                form_version=form_version,
                status="pending",
                submitted_at=now,
                **vars(supplemented_data),
            )
            saved_submission = await self._assessment_submission_repository.save(
                submission
            )
            submission_id = saved_submission.id

        results = await self._risk_scoring_service.evaluate_risk(
            data=supplemented_data, target_scores=target_scores
        )

        for result in results:
            score_entity = RiskScore(
                id=uuid.uuid4(),
                user_id=user_id,
                score_name=result.score_name,
                risk_level=result.risk_level,
                raw_value=result.raw_value,
                normalized_value=result.normalized_value,
                explanation=result.explanation,
                contributing_factors=result.contributing_factors,
                attention_flags=result.attention_flags,
                evaluated_at=now,
                submission_id=submission_id,
            )
            await self._risk_score_repository.save(score_entity)

        if submission_id and self._assessment_submission_repository:
            await self._assessment_submission_repository.update_status(
                submission_id, "completed"
            )

        return results
