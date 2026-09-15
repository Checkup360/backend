import uuid

from app.application.interfaces.file_storage import FileStorage
from app.domain.exceptions import OrganizationNotFoundError
from app.domain.repositories import OrganizationRepository


class DeleteOrganizationLogoUseCase:
    def __init__(
        self,
        org_repo: OrganizationRepository,
        file_storage: FileStorage,
    ) -> None:
        self.org_repo = org_repo
        self.file_storage = file_storage

    async def execute(self, organization_id: uuid.UUID) -> None:
        org = await self.org_repo.get(organization_id)
        if org is None:
            raise OrganizationNotFoundError()

        if org.logo_url:
            await self.file_storage.delete_file(org.logo_url)
            await self.org_repo.update(organization_id, logo_url=None)
