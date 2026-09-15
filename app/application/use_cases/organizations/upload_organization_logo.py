import uuid

from app.application.interfaces.file_storage import FileStorage
from app.domain.exceptions import OrganizationNotFoundError
from app.domain.repositories import OrganizationRepository

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


class UploadOrganizationLogoUseCase:
    def __init__(
        self,
        org_repo: OrganizationRepository,
        file_storage: FileStorage,
    ) -> None:
        self.org_repo = org_repo
        self.file_storage = file_storage

    async def execute(
        self,
        organization_id: uuid.UUID,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        if not content:
            raise ValueError("empty_file")

        if len(content) > MAX_FILE_SIZE_BYTES:
            raise ValueError("file_too_large")

        normalized_type = content_type.lower().split(";")[0].strip()
        if normalized_type not in ALLOWED_MIME_TYPES:
            raise ValueError("invalid_image_format")

        org = await self.org_repo.get(organization_id)
        if org is None:
            raise OrganizationNotFoundError()

        if org.logo_url:
            await self.file_storage.delete_file(org.logo_url)

        new_logo_url = await self.file_storage.save_file(
            content=content,
            filename=filename,
            content_type=normalized_type,
            folder="organizations",
        )

        await self.org_repo.update(organization_id, logo_url=new_logo_url)
        return new_logo_url
