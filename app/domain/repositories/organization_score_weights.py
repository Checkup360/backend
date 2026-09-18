from typing import Protocol
import uuid

from app.domain.entities.organization_score_weights import OrganizationScoreWeights


class OrganizationScoreWeightsRepository(Protocol):
    async def save(
        self, entity: OrganizationScoreWeights
    ) -> OrganizationScoreWeights: ...

    async def get_active_for_organization(
        self, organization_id: uuid.UUID
    ) -> OrganizationScoreWeights | None: ...

    async def get_by_id(self, id: uuid.UUID) -> OrganizationScoreWeights | None: ...

    async def list_versions_for_organization(
        self, organization_id: uuid.UUID
    ) -> list[OrganizationScoreWeights]: ...
