import uuid

from app.domain.repositories import InviteRepository


class DeleteInvites:
    def __init__(self, repository: InviteRepository):
        self.repository = repository

    async def execute(
        self,
        *,
        ids: list[uuid.UUID],
        is_sysadmin: bool,
        organization_id: uuid.UUID | None,
    ) -> int:
        return await self.repository.delete_filtered(
            ids=ids,
            is_sysadmin=is_sysadmin,
            organization_id=organization_id,
        )
