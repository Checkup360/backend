import uuid
from datetime import date
from typing import Protocol

from app.domain.entities import MemberDetails, Membership
from app.domain.repositories import MemberDetailsRepository
from app.domain.value_objects import OrgRole


class MemberUser(Protocol):
    @property
    def id(self) -> uuid.UUID: ...

    @property
    def is_superuser(self) -> bool: ...

    @property
    def membership(self) -> Membership | None: ...


class MemberDetailsService:
    def __init__(self, repo: MemberDetailsRepository):
        self.repo = repo

    def is_member_user(self, user: MemberUser) -> bool:
        if user.is_superuser:
            return False

        if user.membership is None:
            return False
        return OrgRole.MEMBER in user.membership.roles

    async def requires_onboarding(self, user: MemberUser) -> bool:
        if not self.is_member_user(user):
            return False
        return not await self.repo.exists_for_user(user.id)

    async def is_onboarded(self, user_id: uuid.UUID) -> bool:
        return await self.repo.exists_for_user(user_id)

    async def get_profile(self, user_id: uuid.UUID) -> MemberDetails | None:
        return await self.repo.get_by_user(user_id)

    async def complete_onboarding(
        self,
        user: MemberUser,
        date_of_birth: date,
        phone_number: str,
        first_name: str = "",
        last_name: str = "",
    ) -> MemberDetails:
        if date_of_birth > date.today():
            raise ValueError("date_of_birth_in_future")

        return await self.repo.save(
            MemberDetails(
                user_id=user.id,
                date_of_birth=date_of_birth,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
            )
        )

    async def update_profile(
        self,
        user_id: uuid.UUID,
        first_name: str,
        last_name: str,
        phone_number: str | None,
    ) -> MemberDetails:
        details = await self.repo.get_by_user(user_id)
        if details is None:
            raise ValueError("member_details_not_found")

        updated = MemberDetails(
            user_id=user_id,
            date_of_birth=details.date_of_birth,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )
        return await self.repo.save(updated)
