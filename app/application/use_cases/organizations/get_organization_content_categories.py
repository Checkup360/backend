import uuid

from app.application.dto import ContentCategoryDTO
from app.application.interfaces.risk_scoring_service import RiskScoringService
from app.application.use_cases.health_topics.load_health_topics import (
    load_health_topics,
)
from app.domain.exceptions import NotOrganizationAdminError, OrganizationNotFoundError
from app.domain.repositories import MembershipRepository, OrganizationRepository
from app.domain.services.health_topics import is_topic_active
from app.domain.services.risk_score_calculator import DEFAULT_SCORE_WEIGHTS
from app.domain.value_objects import OrgRole

CONTENT_EDITOR_ROLES = {OrgRole.SUPERADMIN, OrgRole.ADMIN, OrgRole.CONTENT_MANAGER}


class GetOrganizationContentCategoriesUseCase:
    """
    Lists every health topic content can be tagged with, flagging the ones the
    organization has enabled. Used by content editors to tag articles.
    """

    def __init__(
        self,
        membership_repo: MembershipRepository,
        organization_repo: OrganizationRepository,
        risk_scoring_service: RiskScoringService,
    ) -> None:
        self._membership_repo = membership_repo
        self._org_repo = organization_repo
        self._risk_scoring_service = risk_scoring_service

    async def execute(
        self,
        actor_user_id: uuid.UUID,
        actor_is_superuser: bool,
        organization_id: uuid.UUID,
    ) -> list[ContentCategoryDTO]:
        organization = await self._org_repo.get(organization_id)
        if organization is None:
            raise OrganizationNotFoundError()
        if not actor_is_superuser:
            await self._ensure_content_editor(actor_user_id, organization_id)

        org_weights = organization.score_weights or DEFAULT_SCORE_WEIGHTS
        topics = await load_health_topics(self._risk_scoring_service)
        return [
            ContentCategoryDTO(
                key=topic.key,
                label=topic.label,
                active=is_topic_active(topic.key, org_weights),
            )
            for topic in topics
        ]

    async def _ensure_content_editor(
        self, actor_user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> None:
        membership = await self._membership_repo.get_by_user_and_org(
            actor_user_id, organization_id
        )
        if membership is None or not CONTENT_EDITOR_ROLES & set(membership.roles):
            raise NotOrganizationAdminError()
