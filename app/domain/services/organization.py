import uuid

from app.domain.entities import Organization
from app.domain.exceptions import OrganizationSlugAlreadyExists
from app.persistence.repositories.organization import OrganizationRepository


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

    async def delete_organization(self, id: uuid.UUID) -> bool:
        return await self.repo.delete(id)
