from fastapi import Depends
from sqlalchemy.exc import IntegrityError

from app.domain.entities import Organization
from app.repositories.organization import (
    OrganizationRepository,
    get_organization_repository,
)


class OrganizationService:
    def __init__(self, repo: OrganizationRepository):
        self.repo = repo

    async def create_organization(self, name: str, slug: str) -> Organization:
        existing = await self.repo.get_by_slug(slug)
        if existing:
            raise ValueError("organization_slug_already_exists")

        try:
            return await self.repo.create(name=name, slug=slug)
        except IntegrityError:
            raise ValueError("organization_slug_already_exists")

    async def list_organizations(self) -> list[Organization]:
        return await self.repo.list()


async def get_organization_service(
    repo: OrganizationRepository = Depends(get_organization_repository),
) -> OrganizationService:
    return OrganizationService(repo)
