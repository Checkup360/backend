import uuid
from app.domain.repositories.organization import OrganizationRepository
from app.domain.services.form_registry import FormDefinition
from app.domain.services.organization_form_policy import OrganizationFormPolicy


class GetActiveMemberFormsUseCase:
    """Use case to retrieve active health form definitions for a member based on org settings."""

    def __init__(
        self,
        organization_repository: OrganizationRepository,
        policy: OrganizationFormPolicy | None = None,
    ) -> None:
        self._organization_repository = organization_repository
        self._policy = policy or OrganizationFormPolicy()

    async def execute(self, organization_id: uuid.UUID | None) -> list[FormDefinition]:
        score_weights = None
        if organization_id is not None:
            org = await self._organization_repository.get_by_id(organization_id)
            if org:
                score_weights = org.score_weights

        return self._policy.get_active_form_definitions(score_weights=score_weights)
