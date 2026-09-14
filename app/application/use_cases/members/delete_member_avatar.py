import uuid

from app.application.interfaces.file_storage import FileStorage
from app.domain.entities import MemberDetails
from app.domain.repositories import MemberDetailsRepository


class DeleteMemberAvatarUseCase:
    def __init__(
        self,
        details_repo: MemberDetailsRepository,
        file_storage: FileStorage,
    ) -> None:
        self.details_repo = details_repo
        self.file_storage = file_storage

    async def execute(self, user_id: uuid.UUID) -> None:
        details = await self.details_repo.get_by_user(user_id)
        if details is None:
            raise ValueError("member_details_not_found")

        if details.avatar_url:
            await self.file_storage.delete_file(details.avatar_url)

        updated_details = MemberDetails(
            user_id=details.user_id,
            date_of_birth=details.date_of_birth,
            first_name=details.first_name,
            last_name=details.last_name,
            phone_number=details.phone_number,
            avatar_url=None,
        )
        await self.details_repo.save(updated_details)
