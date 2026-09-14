import uuid
from datetime import date
import pytest

from app.application.use_cases.members.upload_member_avatar import (
    UploadMemberAvatarUseCase,
    MAX_FILE_SIZE_BYTES,
)
from app.application.use_cases.members.delete_member_avatar import (
    DeleteMemberAvatarUseCase,
)
from app.domain.entities import MemberDetails


class FakeFileStorage:
    def __init__(self):
        self.saved_files = []
        self.deleted_files = []

    async def save_file(
        self,
        content: bytes,
        filename: str,
        content_type: str,
        folder: str = "avatars",
    ) -> str:
        url = f"/media/{folder}/generated-uuid.png"
        self.saved_files.append((content, filename, content_type, url))
        return url

    async def delete_file(self, public_path: str) -> None:
        self.deleted_files.append(public_path)


class FakeMemberDetailsRepo:
    def __init__(self):
        self.details = {}

    async def get_by_user(self, user_id: uuid.UUID) -> MemberDetails | None:
        return self.details.get(user_id)

    async def save(self, entity: MemberDetails) -> MemberDetails:
        self.details[entity.user_id] = entity
        return entity


@pytest.mark.asyncio
async def test_upload_avatar_success():
    repo = FakeMemberDetailsRepo()
    storage = FakeFileStorage()
    use_case = UploadMemberAvatarUseCase(repo, storage)

    user_id = uuid.uuid4()
    repo.details[user_id] = MemberDetails(
        user_id=user_id,
        date_of_birth=date(1990, 1, 1),
        first_name="Alice",
        last_name="Smith",
        avatar_url="/media/avatars/old.png",
    )

    content = b"valid-image-bytes"
    result_url = await use_case.execute(
        user_id=user_id,
        content=content,
        filename="avatar.png",
        content_type="image/png",
    )

    assert result_url == "/media/avatars/generated-uuid.png"
    assert "/media/avatars/old.png" in storage.deleted_files
    assert len(storage.saved_files) == 1
    assert repo.details[user_id].avatar_url == result_url


@pytest.mark.asyncio
async def test_upload_avatar_validations():
    repo = FakeMemberDetailsRepo()
    storage = FakeFileStorage()
    use_case = UploadMemberAvatarUseCase(repo, storage)

    user_id = uuid.uuid4()
    repo.details[user_id] = MemberDetails(
        user_id=user_id,
        date_of_birth=date(1990, 1, 1),
    )

    # Empty content
    with pytest.raises(ValueError, match="empty_file"):
        await use_case.execute(
            user_id=user_id,
            content=b"",
            filename="a.png",
            content_type="image/png",
        )

    # File too large
    with pytest.raises(ValueError, match="file_too_large"):
        await use_case.execute(
            user_id=user_id,
            content=b"x" * (MAX_FILE_SIZE_BYTES + 1),
            filename="a.png",
            content_type="image/png",
        )

    # Invalid MIME
    with pytest.raises(ValueError, match="invalid_image_format"):
        await use_case.execute(
            user_id=user_id,
            content=b"x",
            filename="a.pdf",
            content_type="application/pdf",
        )

    # User details not found
    with pytest.raises(ValueError, match="member_details_not_found"):
        await use_case.execute(
            user_id=uuid.uuid4(),
            content=b"x",
            filename="a.png",
            content_type="image/png",
        )


@pytest.mark.asyncio
async def test_delete_avatar_success():
    repo = FakeMemberDetailsRepo()
    storage = FakeFileStorage()
    use_case = DeleteMemberAvatarUseCase(repo, storage)

    user_id = uuid.uuid4()
    repo.details[user_id] = MemberDetails(
        user_id=user_id,
        date_of_birth=date(1990, 1, 1),
        avatar_url="/media/avatars/existing.png",
    )

    await use_case.execute(user_id=user_id)

    assert "/media/avatars/existing.png" in storage.deleted_files
    assert repo.details[user_id].avatar_url is None


@pytest.mark.asyncio
async def test_delete_avatar_not_found():
    repo = FakeMemberDetailsRepo()
    storage = FakeFileStorage()
    use_case = DeleteMemberAvatarUseCase(repo, storage)

    with pytest.raises(ValueError, match="member_details_not_found"):
        await use_case.execute(user_id=uuid.uuid4())
