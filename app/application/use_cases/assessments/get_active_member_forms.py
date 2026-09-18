import uuid

from app.domain.repositories.organization import OrganizationRepository
from app.domain.repositories.organization_score_weights import (
    OrganizationScoreWeightsRepository,
)
from app.domain.services.form_registry import FormDefinition
from app.domain.services.organization_form_policy import OrganizationFormPolicy


class GetActiveMemberFormsUseCase:
    """Use case to retrieve active health form definitions for a member based on org settings."""

    def __init__(
        self,
        organization_repository: OrganizationRepository | None = None,
        score_weights_repository: OrganizationScoreWeightsRepository | None = None,
        policy: OrganizationFormPolicy | None = None,
    ) -> None:
        self._organization_repository = organization_repository
        self._score_weights_repository = score_weights_repository
        self._policy = policy or OrganizationFormPolicy()

    async def execute(self, organization_id: uuid.UUID | None) -> list[FormDefinition]:
        score_weights = None
        if organization_id is not None:
            if self._score_weights_repository:
                active_weights_rec = (
                    await self._score_weights_repository.get_active_for_organization(
                        organization_id
                    )
                )
                if active_weights_rec:
                    score_weights = active_weights_rec.weights
            if score_weights is None and self._organization_repository:
                org = await self._organization_repository.get(organization_id)
                if org:
                    score_weights = org.score_weights

        return self._policy.get_active_form_definitions(score_weights=score_weights)
