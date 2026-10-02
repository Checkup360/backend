import uuid

from app.application.dto import ContentCategoryDTO, MemberRiskPrioritiesDTO
from app.application.interfaces.risk_scoring_service import RiskScoringService
from app.application.use_cases.health_topics.load_health_topics import (
    load_health_topics,
)
from app.domain.repositories.organization import OrganizationRepository
from app.domain.repositories.risk_score import RiskScoreRepository
from app.domain.services.member_risk_priorities import calculate_member_risk_weights


class GetMemberRiskPrioritiesUseCase:
    """Use case to evaluate clinical risk priorities and weights for a member."""

    def __init__(
        self,
        risk_score_repo: RiskScoreRepository,
        organization_repo: OrganizationRepository,
        risk_scoring_service: RiskScoringService,
    ) -> None:
        self._risk_score_repo = risk_score_repo
        self._org_repo = organization_repo
        self._risk_scoring_service = risk_scoring_service

    async def execute(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID | None = None,
    ) -> MemberRiskPrioritiesDTO:
        scores = await self._risk_score_repo.get_by_user_id(user_id)
        topics = await load_health_topics(self._risk_scoring_service)

        org_weights: dict[str, float] | None = None
        if organization_id is not None:
            org = await self._org_repo.get(organization_id)
            if org and org.score_weights:
                org_weights = org.score_weights

        risk_weights = calculate_member_risk_weights(
            scores, [topic.key for topic in topics], org_weights
        )
        highest_risk = (
            max(risk_weights.items(), key=lambda item: item[1])[0]
            if risk_weights
            else None
        )
        # Weights only contain active topics, so they define the visible categories
        categories = [
            ContentCategoryDTO(key=topic.key, label=topic.label, active=True)
            for topic in topics
            if topic.key in risk_weights
        ]

        return MemberRiskPrioritiesDTO(
            user_id=user_id,
            risk_weights=risk_weights,
            highest_risk=highest_risk,
            categories=categories,
        )
