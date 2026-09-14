import uuid

from app.application.interfaces.file_storage import FileStorage
from app.domain.entities import MemberDetails
from app.domain.repositories import MemberDetailsRepository

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


class UploadMemberAvatarUseCase:
    def __init__(
        self,
        details_repo: MemberDetailsRepository,
        file_storage: FileStorage,
    ) -> None:
        self.details_repo = details_repo
        self.file_storage = file_storage

    async def execute(
        self,
        user_id: uuid.UUID,
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

        details = await self.details_repo.get_by_user(user_id)
        if details is None:
            raise ValueError("member_details_not_found")

        if details.avatar_url:
            await self.file_storage.delete_file(details.avatar_url)

        new_avatar_url = await self.file_storage.save_file(
            content=content,
            filename=filename,
            content_type=normalized_type,
            folder="avatars",
        )

        updated_details = MemberDetails(
            user_id=details.user_id,
            date_of_birth=details.date_of_birth,
            first_name=details.first_name,
            last_name=details.last_name,
            phone_number=details.phone_number,
            avatar_url=new_avatar_url,
        )
        await self.details_repo.save(updated_details)

        return new_avatar_url
