"""Use case for smart recalculation of member risk scores."""

from datetime import date, datetime, timezone
import uuid

from app.application.interfaces.risk_scoring_service import RiskScoringService
from app.domain.entities.risk_score import RiskScore
from app.domain.repositories.member_health_data import MemberHealthDataRepository
from app.domain.repositories.member_details import MemberDetailsRepository
from app.domain.repositories.risk_score import RiskScoreRepository


class RecalculateMemberScoresUseCase:
    """
    Evaluates and persists risk scores for a member based on complete required fields
    and updated field triggers.
    """

    def __init__(
        self,
        member_health_data_repo: MemberHealthDataRepository,
        member_details_repo: MemberDetailsRepository,
        risk_score_repo: RiskScoreRepository,
        risk_scoring_service: RiskScoringService,
    ) -> None:
        self._health_data_repo = member_health_data_repo
        self._details_repo = member_details_repo
        self._risk_score_repo = risk_score_repo
        self._risk_scoring_service = risk_scoring_service

    async def execute(
        self,
        user_id: uuid.UUID,
        updated_fields: set[str] | list[str] | None = None,
        submission_id: uuid.UUID | None = None,
    ) -> list[RiskScore]:
        """
        Executes dynamic score evaluation for eligible scores.

        Args:
            user_id: The ID of the member user.
            updated_fields: Optional set/list of field names that were updated in current action.

        Returns:
            List of newly evaluated and persisted RiskScore entities.
        """
        member_health = await self._health_data_repo.get_by_user(user_id)
        if not member_health:
            return []

        details = await self._details_repo.get_by_user(user_id)
        age: int | None = None
        if details and details.date_of_birth:
            age = self._calculate_age(details.date_of_birth)

        # Build map of available member health data
        health_data: dict[str, str | int | float | bool] = {}
        if age is not None:
            health_data["age"] = age
        if member_health.biological_sex is not None:
            health_data["sex"] = member_health.biological_sex
        if member_health.height is not None:
            h = float(member_health.height)
            health_data["height"] = h / 100.0 if h > 3.0 else h
        if member_health.weight is not None:
            health_data["weight"] = member_health.weight
        if member_health.waist_circumference is not None:
            health_data["waist_circumference"] = member_health.waist_circumference
        if member_health.triglycerides is not None:
            health_data["triglycerides"] = member_health.triglycerides
        if member_health.total_cholesterol is not None:
            health_data["total_cholesterol"] = member_health.total_cholesterol
        if member_health.hdl_cholesterol is not None:
            health_data["hdl_cholesterol"] = member_health.hdl_cholesterol
        if member_health.systolic_blood_pressure is not None:
            health_data["systolic_blood_pressure"] = (
                member_health.systolic_blood_pressure
            )
        if member_health.diastolic_blood_pressure is not None:
            health_data["diastolic_blood_pressure"] = (
                member_health.diastolic_blood_pressure
            )
        if member_health.fasting_glucose is not None:
            health_data["fasting_glucose"] = member_health.fasting_glucose
        if member_health.glucose_lowering_medication is not None:
            health_data["glucose_lowering_medication"] = (
                member_health.glucose_lowering_medication
            )
        if member_health.neck_circumference is not None:
            health_data["neck_circumference"] = member_health.neck_circumference
        if member_health.snoring is not None:
            health_data["snoring"] = member_health.snoring
        if member_health.tired is not None:
            health_data["tired"] = member_health.tired
        if member_health.observed_apnea is not None:
            health_data["observed_apnea"] = member_health.observed_apnea
        if member_health.smoker is not None:
            health_data["smoker"] = member_health.smoker
        if member_health.hypertension_medication is not None:
            health_data["hypertension_medication"] = (
                member_health.hypertension_medication
            )
        if member_health.daily_physical_activity is not None:
            health_data["daily_physical_activity"] = (
                member_health.daily_physical_activity
            )
        if member_health.fruits_vegetables is not None:
            health_data["fruits_vegetables"] = member_health.fruits_vegetables
        if member_health.previous_high_glucose is not None:
            health_data["previous_high_glucose"] = member_health.previous_high_glucose
        if member_health.family_diabetes is not None:
            health_data["family_diabetes"] = member_health.family_diabetes
        if member_health.little_interest is not None:
            health_data["little_interest"] = member_health.little_interest
        if member_health.feeling_down is not None:
            health_data["feeling_down"] = member_health.feeling_down
        if member_health.sleep_trouble is not None:
            health_data["sleep_trouble"] = member_health.sleep_trouble
        if member_health.tired_energy is not None:
            health_data["tired_energy"] = member_health.tired_energy
        if member_health.appetite is not None:
            health_data["appetite"] = member_health.appetite
        if member_health.feeling_bad is not None:
            health_data["feeling_bad"] = member_health.feeling_bad
        if member_health.concentration is not None:
            health_data["concentration"] = member_health.concentration
        if member_health.psychomotor is not None:
            health_data["psychomotor"] = member_health.psychomotor
        if member_health.self_harm_thoughts is not None:
            health_data["self_harm_thoughts"] = member_health.self_harm_thoughts
        if member_health.eoss_physical_health_stage is not None:
            health_data["physical_health_stage"] = (
                member_health.eoss_physical_health_stage
            )
        if member_health.eoss_mental_health_stage is not None:
            health_data["mental_health_stage"] = member_health.eoss_mental_health_stage
        if member_health.eoss_functional_stage is not None:
            health_data["functional_stage"] = member_health.eoss_functional_stage

        catalog = await self._risk_scoring_service.get_catalog()
        existing_scores = await self._risk_score_repo.get_by_user_id(user_id)
        existing_score_ids = {s.score_name.lower(): s for s in existing_scores}

        updated_set = set(updated_fields) if updated_fields is not None else None
        now = datetime.now(timezone.utc)
        evaluated_scores: list[RiskScore] = []

        for item in catalog:
            # Rule 1: 100% of required_fields must be present
            has_all_required = all(
                field_name in health_data and health_data[field_name] is not None
                for field_name in item.required_fields
            )
            if not has_all_required:
                continue

            # Rule 2: Must be new evaluation OR updated_fields is None OR at least 1 field used was updated
            all_score_fields = set(item.required_fields + item.optional_fields)
            is_new = item.score_id not in existing_score_ids
            has_changes = (
                updated_set is None
                or any(f in updated_set for f in all_score_fields)
                or ("biological_sex" in updated_set and "sex" in all_score_fields)
            )

            # A form submission represents a complete snapshot. When it is
            # available, attach every currently calculable score to it.
            if submission_id is not None:
                should_evaluate = True
            else:
                should_evaluate = is_new or has_changes

            if not should_evaluate:
                continue

            # Build payload for single score evaluation
            payload: dict[str, str | int | float | bool] = {}
            for field_name in item.required_fields + item.optional_fields:
                if field_name in health_data and health_data[field_name] is not None:
                    payload[field_name] = health_data[field_name]

            res = await self._risk_scoring_service.evaluate_single_score(
                item.score_id, payload
            )

            if res.status == "CALCULATED":
                entity = RiskScore(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    score_name=res.score_name,
                    risk_level=res.risk_level,
                    raw_value=res.raw_value,
                    normalized_value=res.normalized_value,
                    explanation=res.explanation,
                    contributing_factors=res.contributing_factors,
                    attention_flags=res.attention_flags,
                    evaluated_at=now,
                    submission_id=submission_id,
                )
                await self._risk_score_repo.save(entity)
                evaluated_scores.append(entity)

        return evaluated_scores

    @staticmethod
    def _calculate_age(date_of_birth: date) -> int:
        today = date.today()
        return (
            today.year
            - date_of_birth.year
            - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
        )
