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
            health_data["height"] = member_health.height
        if member_health.weight is not None:
            health_data["weight"] = member_health.weight
        if member_health.waist_circumference is not None:
            health_data["waist_circumference"] = member_health.waist_circumference
        if member_health.neck_circumference is not None:
            health_data["neck_circumference"] = member_health.neck_circumference
        if member_health.snoring is not None:
            health_data["snoring"] = member_health.snoring
        if member_health.tired is not None:
            health_data["tired"] = member_health.tired
        if member_health.observed_apnea is not None:
            health_data["observed_apnea"] = member_health.observed_apnea
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

        catalog = await self._risk_scoring_service.get_catalog()
        existing_scores = await self._risk_score_repo.get_by_user_id(user_id)
        existing_score_ids = {s.score_name.lower(): s for s in existing_scores}

        updated_set = set(updated_fields) if updated_fields is not None else None
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

            if not (is_new or has_changes):
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
                    evaluated_at=datetime.now(timezone.utc),
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
