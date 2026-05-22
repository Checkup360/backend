from datetime import date

from app.domain.entities import MemberDetails
from app.domain.entities.org_role import OrgRole
from app.persistence.models import User
from app.persistence.repositories.member_details import MemberDetailsRepository


class MemberDetailsService:
    def __init__(self, repo: MemberDetailsRepository):
        self.repo = repo

    def is_member_only_user(self, user: User) -> bool:
        if user.is_superuser:
            return False

        roles = {role for membership in user.memberships for role in membership.roles}
        return OrgRole.MEMBER in roles and OrgRole.ADMIN not in roles

    async def requires_onboarding(self, user: User) -> bool:
        if not self.is_member_only_user(user):
            return False
        return not await self.repo.exists_for_user(user.id)

    async def complete_onboarding(
        self, user: User, date_of_birth: date
    ) -> MemberDetails:
        if date_of_birth > date.today():
            raise ValueError("date_of_birth_in_future")

        return await self.repo.save(
            MemberDetails(user_id=user.id, date_of_birth=date_of_birth)
        )
