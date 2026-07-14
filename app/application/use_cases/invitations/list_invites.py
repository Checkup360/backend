import uuid

from app.domain.entities import InviteToken
from app.domain.repositories import InviteRepository
from app.domain.value_objects import OrgRole


class ListInvites:
    def __init__(self, repository: InviteRepository):
        self.repository = repository

    async def execute(
        self,
        *,
        organization_id: uuid.UUID | None,
        is_sysadmin: bool,
        role: str | None,
        status: str | None,
        page: int | None,
        page_size: int,
    ) -> tuple[list[InviteToken], int]:
        parsed_role = None
        if role is not None:
            try:
                parsed_role = OrgRole(role.lower())
            except ValueError:
                parsed_role = None
        normalized_status = status.lower() if status else None
        return await self.repository.list_filtered(
            organization_id=organization_id,
            is_sysadmin=is_sysadmin,
            role=parsed_role,
            status=normalized_status,
            page=page,
            page_size=page_size,
        )
