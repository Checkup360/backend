import uuid

from app.application.use_cases.members.member_details_service import (
    MemberDetailsService,
)
from app.application.use_cases.memberships.membership_service import MembershipService
from app.domain.entities.employee_summary import EmployeeSummary
from app.domain.repositories import EmployeeDirectoryRepository
from app.domain.services.form_registry import FormRegistry
from app.domain.value_objects import (
    EmployeeDirectoryQuery,
    EmployeeSortField,
    MembershipState,
    OrgRole,
    ScoreFilter,
    SortDirection,
)


class ListOrganizationEmployeesUseCase:
    def __init__(
        self,
        membership_service: MembershipService,
        member_details_service: MemberDetailsService,
        employee_directory_repo: EmployeeDirectoryRepository,
        form_registry: FormRegistry,
    ):
        self._membership_service = membership_service
        self._member_details_service = member_details_service
        self._employee_directory_repo = employee_directory_repo
        self._form_registry = form_registry

    async def execute(
        self,
        actor_user_id: uuid.UUID,
        organization_id: uuid.UUID,
        roles: list[OrgRole] | None = None,
        state: MembershipState = MembershipState.ALL,
        department_id: uuid.UUID | None = None,
        status: str | None = None,
        score_filter: ScoreFilter | None = None,
        search: str | None = None,
        sort_by: EmployeeSortField | None = None,
        sort_direction: SortDirection = SortDirection.ASC,
        page: int | None = None,
        page_size: int = 10,
    ) -> tuple[list[EmployeeSummary], int]:
        await self._membership_service.get_admin_membership(
            actor_user_id, organization_id
        )
        required_forms = (
            await self._member_details_service.get_required_forms_for_organization(
                organization_id
            )
        )
        form_fields = self._form_registry.get_form_fields_map()
        query = EmployeeDirectoryQuery(
            roles=roles,
            state=state,
            department_id=department_id,
            status=status,
            score_filter=score_filter,
            search=search,
            sort_by=sort_by,
            sort_direction=sort_direction,
            required_form_fields={
                form_type: form_fields.get(form_type, [])
                for form_type in required_forms
            },
            page=page,
            page_size=page_size,
        )
        return await self._employee_directory_repo.search(organization_id, query)
