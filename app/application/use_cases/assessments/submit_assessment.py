import uuid

from app.application.dto.risk_scoring import HealthDataDTO, ScoreResultDTO
from app.application.interfaces.risk_scoring_service import RiskScoringService
from app.domain.repositories.member_details import MemberDetailsRepository
from app.domain.repositories.risk_score import RiskScoreRepository
from app.domain.entities.risk_score import RiskScore
from app.domain.services.time_provider import TimeProvider


class SubmitAssessmentUseCase:
    def __init__(
        self,
        risk_scoring_service: RiskScoringService,
        member_details_repository: MemberDetailsRepository,
        risk_score_repository: RiskScoreRepository,
        time_provider: TimeProvider,
    ) -> None:
        self._risk_scoring_service = risk_scoring_service
        self._member_details_repository = member_details_repository
        self._risk_score_repository = risk_score_repository
        self._time_provider = time_provider

    async def execute(
        self,
        user_id: uuid.UUID,
        health_data: HealthDataDTO,
        target_scores: list[str] | None = None,
    ) -> list[ScoreResultDTO]:
        # Retrieve member details to supplement the health data
        member_details = await self._member_details_repository.get_by_user(user_id)
        if not member_details:
            raise ValueError("Member details not found. Please complete onboarding.")

        # Calculate age
        today = self._time_provider.today()
        dob = member_details.date_of_birth
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        # Create a new HealthDataDTO with age supplemented
        supplemented_data = HealthDataDTO(
            age=age,
            sex=health_data.sex,
            weight=health_data.weight,
            height=health_data.height,
            waist_circumference=health_data.waist_circumference,
            systolic_blood_pressure=health_data.systolic_blood_pressure,
            total_cholesterol=health_data.total_cholesterol,
            hdl=health_data.hdl,
            triglycerides=health_data.triglycerides,
            smoker=health_data.smoker,
            daily_physical_activity=health_data.daily_physical_activity,
            fruits_vegetables=health_data.fruits_vegetables,
            hypertension_medication=health_data.hypertension_medication,
            previous_high_glucose=health_data.previous_high_glucose,
            family_diabetes=health_data.family_diabetes,
            snoring=health_data.snoring,
            tired=health_data.tired,
            observed_apnea=health_data.observed_apnea,
            neck_circumference=health_data.neck_circumference,
        )

        results = await self._risk_scoring_service.evaluate_risk(
            data=supplemented_data, target_scores=target_scores
        )

        # Save scores to database
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
                evaluated_at=self._time_provider.utcnow(),
            )
            await self._risk_score_repository.save(score_entity)

        return results
