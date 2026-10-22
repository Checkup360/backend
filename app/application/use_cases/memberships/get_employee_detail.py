import uuid

from app.application.dto.employee_detail import EmployeeDetailDTO
from app.application.use_cases.members.member_details_service import (
    MemberDetailsService,
)
from app.application.use_cases.memberships.membership_service import (
    MembershipService,
)
from app.domain.exceptions import MembershipNotFoundError
from app.domain.repositories import MembershipRepository
from app.domain.services.employee_status import determine_employee_status
from app.domain.value_objects import OrgRole


class GetEmployeeDetailUseCase:
    """Returns a single employee of an organization to one of its admins."""

    def __init__(
        self,
        membership_service: MembershipService,
        membership_repo: MembershipRepository,
        member_details_service: MemberDetailsService,
    ):
        self.membership_service = membership_service
        self.membership_repo = membership_repo
        self.member_details_service = member_details_service

    async def execute(
        self,
        actor_user_id: uuid.UUID,
        actor_is_superuser: bool,
        organization_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> EmployeeDetailDTO:
        if not actor_is_superuser:
            await self.membership_service.get_admin_membership(
                actor_user_id, organization_id
            )
        employee = await self.membership_repo.get_employee(
            target_user_id, organization_id
        )
        if not employee:
            raise MembershipNotFoundError()

        profile = await self.member_details_service.get_profile(target_user_id)
        onboarded = profile is not None
        completed_all_forms = (
            onboarded
            and OrgRole.MEMBER in employee.roles
            and await self.member_details_service.has_completed_all_forms(
                target_user_id, organization_id=organization_id
            )
        )
        status = determine_employee_status(
            employee.roles, onboarded, completed_all_forms
        )
        return EmployeeDetailDTO(employee=employee, profile=profile, status=status)
