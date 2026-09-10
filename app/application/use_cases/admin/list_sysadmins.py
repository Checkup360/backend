from dataclasses import dataclass

from app.domain.entities import MemberDetails, User
from app.domain.repositories import InviteRepository, UserRepository


@dataclass
class SysadminItemDTO:
    user: User
    details: MemberDetails | None


@dataclass
class SysadminStatsDTO:
    total_sysadmins: int
    active_sysadmins: int
    pending_invites: int


class ListSysadminsUseCase:
    def __init__(self, user_repo: UserRepository, invite_repo: InviteRepository):
        self._user_repo = user_repo
        self._invite_repo = invite_repo

    async def list_sysadmins(
        self,
        search: str | None = None,
        is_active: bool | None = None,
        page: int | None = None,
        page_size: int = 10,
    ) -> tuple[list[SysadminItemDTO], int]:
        rows, total = await self._user_repo.list_sysadmins(
            search=search,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )
        items = [SysadminItemDTO(user=u, details=d) for u, d in rows]
        return items, total

    async def get_stats(self) -> SysadminStatsDTO:
        total = await self._user_repo.count_sysadmins()
        active = await self._user_repo.count_sysadmins(is_active=True)
        _, pending_count = await self._invite_repo.list_filtered(
            organization_id=None,
            is_sysadmin=True,
            role=None,
            status="active",
            page=1,
            page_size=1,
        )
        return SysadminStatsDTO(
            total_sysadmins=total,
            active_sysadmins=active,
            pending_invites=pending_count,
        )
