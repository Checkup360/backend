import uuid

from app.domain.entities import Organization
from app.domain.exceptions import (
    OrganizationNotFoundError,
    OrganizationSlugAlreadyExists,
)
from app.domain.repositories import OrganizationRepository
from app.domain.services.risk_score_calculator import DEFAULT_SCORE_WEIGHTS


class OrganizationService:
    def __init__(self, repo: OrganizationRepository):
        self.repo = repo

    async def create_organization(self, name: str, slug: str) -> Organization:
        existing = await self.repo.get_by_slug(slug)
        if existing:
            raise OrganizationSlugAlreadyExists()

        return await self.repo.create(name=name, slug=slug)

    async def list_organizations(self) -> list[Organization]:
        return await self.repo.list()

    async def get_organization(self, id: uuid.UUID) -> Organization | None:
        return await self.repo.get(id)

    async def delete_organization(self, id: uuid.UUID) -> bool:
        return await self.repo.delete(id)

    async def get_score_weights(self, id: uuid.UUID) -> dict[str, float]:
        org = await self.repo.get(id)
        if not org:
            raise OrganizationNotFoundError()
        if not org.score_weights:
            return dict(DEFAULT_SCORE_WEIGHTS)
        return org.score_weights

    async def update_score_weights(
        self, id: uuid.UUID, score_weights: dict[str, float]
    ) -> Organization:
        org = await self.repo.get(id)
        if not org:
            raise OrganizationNotFoundError()
        for k, v in score_weights.items():
            if not isinstance(v, (int, float)) or v < 0:
                raise ValueError(f"Invalid weight value for '{k}'")
        updated = await self.repo.update_score_weights(id, score_weights)
        if not updated:
            raise OrganizationNotFoundError()
        return updated

    async def update_organization_name(self, id: uuid.UUID, name: str) -> Organization:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("organization_name_empty")
        org = await self.repo.get(id)
        if not org:
            raise OrganizationNotFoundError()
        updated = await self.repo.update(id, name=cleaned_name)
        if not updated:
            raise OrganizationNotFoundError()
        return updated
