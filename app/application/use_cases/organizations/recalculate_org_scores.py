"""Use case for recalculating all member overall scores when organization weights change."""

import uuid
from datetime import datetime, timezone

from app.domain.entities.member_overall_score import MemberOverallScore
from app.domain.repositories.member_overall_score import MemberOverallScoreRepository
from app.domain.repositories.membership import MembershipRepository
from app.domain.repositories.organization_score_weights import (
    OrganizationScoreWeightsRepository,
)
from app.domain.repositories.risk_score import RiskScoreRepository
from app.domain.services.risk_score_calculator import (
    DEFAULT_SCORE_WEIGHTS,
    calculate_weighted_overall_score,
)


class RecalculateOrganizationOverallScoresUseCase:
    """
    Recalculates and persists MemberOverallScore for all members of an organization.
    Typically run as a background task when organization score weights are updated.
    """

    def __init__(
        self,
        membership_repo: MembershipRepository,
        risk_score_repo: RiskScoreRepository,
        member_overall_score_repo: MemberOverallScoreRepository,
        score_weights_repo: OrganizationScoreWeightsRepository,
    ):
        self._membership_repo = membership_repo
        self._risk_score_repo = risk_score_repo
        self._member_overall_score_repo = member_overall_score_repo
        self._score_weights_repo = score_weights_repo

    async def execute(self, organization_id: uuid.UUID) -> None:
        """
        Executes the recalculation for all members in the given organization.
        """
        # 1. Fetch active weights
        weights_record = await self._score_weights_repo.get_active_for_organization(
            organization_id
        )
        weights = weights_record.weights if weights_record else DEFAULT_SCORE_WEIGHTS
        weights_record_id = weights_record.id if weights_record else None

        # 2. Fetch all members
        employees = await self._membership_repo.list_members_for_organization(
            organization_id
        )

        # 3. For each member, recalculate and persist overall score
        for employee in employees:
            user_scores = await self._risk_score_repo.get_by_user_id(employee.user.id)
            overall_health_index, risk_level = calculate_weighted_overall_score(
                user_scores, weights
            )

            if overall_health_index is not None and risk_level is not None:
                overall_entity = MemberOverallScore(
                    id=uuid.uuid4(),
                    user_id=employee.user.id,
                    organization_id=organization_id,
                    score_weights_id=weights_record_id,
                    submission_id=None,
                    overall_health_index=overall_health_index,
                    risk_level=risk_level,
                    evaluated_at=datetime.now(timezone.utc),
                )
                await self._member_overall_score_repo.save(overall_entity)
