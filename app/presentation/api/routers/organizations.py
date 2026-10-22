from datetime import datetime
import uuid
from typing import NoReturn

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)

from app.presentation.api.authorization import require_superuser
from app.application.dto import AuthenticatedUser
from app.presentation.api.dependencies import (
    get_department_service,
    get_current_user,
    get_delete_organization_logo_use_case,
    get_membership_service,
    get_organization_service,
    get_upload_organization_logo_use_case,
    get_member_details_service,
    get_get_assessments_use_case,
    get_organization_analytics_use_case,
    get_assessment_submissions_use_case,
    get_member_overall_score_repository,
    get_update_employee_roles_use_case,
    get_employee_detail_use_case,
    get_list_organization_employees_use_case,
    get_recalculate_org_scores_use_case,
    get_organization_content_categories_use_case,
    get_get_organization_audit_logs_use_case,
    get_get_organization_compliance_summary_use_case,
)
from app.application.dto.employee_detail import EmployeeDetailDTO
from app.application.use_cases.memberships.get_employee_detail import (
    GetEmployeeDetailUseCase,
)
from app.application.use_cases.organizations.recalculate_org_scores import (
    RecalculateOrganizationOverallScoresUseCase,
)
from app.application.use_cases.organizations.get_organization_content_categories import (
    GetOrganizationContentCategoriesUseCase,
)
from app.domain.repositories.member_overall_score import MemberOverallScoreRepository
from app.application.use_cases.organizations import (
    DeleteOrganizationLogoUseCase,
    GetOrganizationAnalyticsUseCase,
    UploadOrganizationLogoUseCase,
)
from app.application.use_cases.audit import (
    GetOrganizationAuditLogsUseCase,
    GetOrganizationComplianceSummaryUseCase,
)
from app.presentation.api.response_models.audit_logs import (
    AuditLogItemResponse,
    AuditLogListResponse,
    ConsentComplianceSummaryResponse,
)
from app.presentation.api.response_models.analytics import (
    DepartmentAnalyticsSummaryResponse,
    RegistrationTrendPointResponse,
    RiskTrendPointResponse,
)
from app.application.use_cases.memberships.list_organization_employees import (
    ListOrganizationEmployeesUseCase,
)
from app.domain.entities.employee_summary import EmployeeSummary
from app.domain.value_objects.employee_directory_query import ScoreFilter
from app.domain.value_objects.membership_state import MembershipState
from app.domain.services.employee_status import determine_employee_status
from app.domain.value_objects.org_role import OrgRole
from app.domain.exceptions import (
    CannotRemoveLastSuperadminError,
    CannotRemoveOwnSuperadminError,
    DepartmentInUseError,
    DepartmentNotFoundError,
    DepartmentSlugAlreadyExists,
    HealthTopicsUnavailableError,
    InsufficientRolePermissionError,
    MembershipNotFoundError,
    NotOrganizationAdminError,
    OrganizationNotFoundError,
    OrganizationSlugAlreadyExists,
)
from app.application.use_cases.departments.department_service import DepartmentService
from app.application.use_cases.memberships.membership_service import MembershipService
from app.application.use_cases.memberships.update_employee_roles import (
    UpdateEmployeeRolesUseCase,
)
from app.application.use_cases.members.member_details_service import (
    MemberDetailsService,
)
from app.application.use_cases.organizations.organization_service import (
    OrganizationService,
)
from app.application.use_cases.assessments.get_assessments import GetAssessmentsUseCase
from app.application.use_cases.assessments.get_submissions import (
    GetAssessmentSubmissionsUseCase,
)
from app.presentation.api.request_models.organization import (
    AssignDepartmentRequest,
    CreateOrganizationRequest,
    DepartmentRequest,
    ScoreWeightsRequest,
    UpdateEmployeeRolesRequest,
    UpdateOrganizationRequest,
)
from app.presentation.api.response_models.organization import (
    DepartmentResponse,
    EmployeeDetailResponse,
    OrganizationEmployeeResponse,
    OrganizationLogoResponse,
    OrganizationResponse,
    OrganizationSummaryResponse,
    ScoreWeightsResponse,
)
from app.presentation.api.response_models.assessments import (
    AssessmentsResponse,
    AssessmentResultResponse,
)
from app.presentation.api.routers.assessments import (
    _format_score_display_name,
    build_assessments_response,
    _submission_detail_response,
)
from app.presentation.api.response_models.assessment_submissions import (
    AssessmentSubmissionDetailResponse,
    AssessmentSubmissionListResponse,
    AssessmentSubmissionSummaryResponse,
)

from app.presentation.api.response_models.content_category import (
    ContentCategoryResponse,
)

router = APIRouter(prefix="/organizations", tags=["orgs"])


@router.get("", response_model=list[OrganizationResponse])
@router.get("/", response_model=list[OrganizationResponse], include_in_schema=False)
async def list_organizations(
    response: Response,
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    service: OrganizationService = Depends(get_organization_service),
    current_user: AuthenticatedUser = Depends(require_superuser),
):
    orgs, total = await service.search_organizations(
        status=status_filter, search=search, page=page, page_size=page_size
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Page"] = str(page or 1)
    return orgs


@router.post(
    "", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED
)
@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_organization(
    request: CreateOrganizationRequest,
    service: OrganizationService = Depends(get_organization_service),
    current_user: AuthenticatedUser = Depends(require_superuser),
):
    try:
        organization = await service.create_organization(
            name=request.name, slug=request.slug
        )
    except OrganizationSlugAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="organization_slug_already_exists",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="unknown_error",
        )

    return organization


@router.get("/{organization_id}/summary", response_model=OrganizationSummaryResponse)
async def get_organization_summary(
    organization_id: uuid.UUID,
    organization_service: OrganizationService = Depends(get_organization_service),
    membership_service: MembershipService = Depends(get_membership_service),
    _: AuthenticatedUser = Depends(require_superuser),
):
    organization = await organization_service.get_organization(organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )

    total_members = await membership_service.count_members_for_organization(
        organization_id
    )
    total_employees = await membership_service.count_members_for_organization(
        organization_id, roles=[OrgRole.MEMBER]
    )
    total_admins = await membership_service.count_members_for_organization(
        organization_id, roles=[OrgRole.ADMIN]
    )
    total_content_managers = await membership_service.count_members_for_organization(
        organization_id, roles=[OrgRole.CONTENT_MANAGER]
    )

    return OrganizationSummaryResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        total_members=total_members,
        total_employees=total_employees,
        total_admins=total_admins,
        total_content_managers=total_content_managers,
        logo_url=organization.logo_url,
    )


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    organization_service: OrganizationService = Depends(get_organization_service),
    membership_service: MembershipService = Depends(get_membership_service),
):
    try:
        if not current_user.is_superuser:
            await membership_service.get_admin_membership(
                current_user.id, organization_id
            )
        org = await organization_service.get_organization(organization_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="organization_not_found",
            )
        return org
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: uuid.UUID,
    request: UpdateOrganizationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    organization_service: OrganizationService = Depends(get_organization_service),
    membership_service: MembershipService = Depends(get_membership_service),
):
    try:
        if not current_user.is_superuser:
            await membership_service.get_admin_membership(
                current_user.id, organization_id
            )
        updated_org = await organization_service.update_organization_name(
            organization_id, request.name
        )
        return updated_org
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{organization_id}/logo", response_model=OrganizationLogoResponse)
async def upload_organization_logo(
    organization_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
    upload_use_case: UploadOrganizationLogoUseCase = Depends(
        get_upload_organization_logo_use_case
    ),
    membership_service: MembershipService = Depends(get_membership_service),
):
    try:
        if not current_user.is_superuser:
            await membership_service.get_admin_membership(
                current_user.id, organization_id
            )
        content = await file.read()
        logo_url = await upload_use_case.execute(
            organization_id=organization_id,
            content=content,
            filename=file.filename or "logo.png",
            content_type=file.content_type or "image/png",
        )
        return OrganizationLogoResponse(logo_url=logo_url)
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.delete("/{organization_id}/logo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization_logo(
    organization_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    delete_use_case: DeleteOrganizationLogoUseCase = Depends(
        get_delete_organization_logo_use_case
    ),
    membership_service: MembershipService = Depends(get_membership_service),
):
    try:
        if not current_user.is_superuser:
            await membership_service.get_admin_membership(
                current_user.id, organization_id
            )
        await delete_use_case.execute(organization_id)
        return None
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: uuid.UUID,
    service: OrganizationService = Depends(get_organization_service),
    _: AuthenticatedUser = Depends(require_superuser),
):
    deleted = await service.delete_organization(id=organization_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )


def _map_department_error(exc: Exception) -> NoReturn:
    if isinstance(exc, OrganizationNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    if isinstance(exc, NotOrganizationAdminError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    if isinstance(exc, DepartmentNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="department_not_found",
        )
    if isinstance(exc, DepartmentSlugAlreadyExists):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="department_slug_already_exists",
        )
    if isinstance(exc, DepartmentInUseError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="department_in_use",
        )
    if isinstance(exc, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    raise exc


@router.get("/{organization_id}/departments", response_model=list[DepartmentResponse])
async def list_departments(
    organization_id: uuid.UUID,
    response: Response,
    search: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    department_service: DepartmentService = Depends(get_department_service),
):
    try:
        if current_user.is_superuser:
            (
                departments,
                total,
            ) = await department_service.search_departments_as_superuser(
                organization_id, search=search, page=page, page_size=page_size
            )
        else:
            departments, total = await department_service.search_departments(
                current_user.id,
                organization_id,
                search=search,
                page=page,
                page_size=page_size,
            )
    except Exception as exc:
        _map_department_error(exc)

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Page"] = str(page or 1)
    return departments


@router.post(
    "/{organization_id}/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_department(
    organization_id: uuid.UUID,
    request: DepartmentRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    department_service: DepartmentService = Depends(get_department_service),
):
    try:
        return await department_service.create_department(
            current_user.id, organization_id, request.name
        )
    except Exception as exc:
        _map_department_error(exc)


@router.patch(
    "/{organization_id}/departments/{department_id}",
    response_model=DepartmentResponse,
)
async def update_department(
    organization_id: uuid.UUID,
    department_id: uuid.UUID,
    request: DepartmentRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    department_service: DepartmentService = Depends(get_department_service),
):
    try:
        return await department_service.update_department(
            current_user.id, organization_id, department_id, request.name
        )
    except Exception as exc:
        _map_department_error(exc)


@router.delete(
    "/{organization_id}/departments/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_department(
    organization_id: uuid.UUID,
    department_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    department_service: DepartmentService = Depends(get_department_service),
):
    try:
        await department_service.delete_department(
            current_user.id, organization_id, department_id
        )
    except Exception as exc:
        _map_department_error(exc)


@router.patch(
    "/{organization_id}/employees/{user_id}/department",
    response_model=OrganizationEmployeeResponse,
)
async def assign_employee_department(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    request: AssignDepartmentRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    department_service: DepartmentService = Depends(get_department_service),
    member_details_service: MemberDetailsService = Depends(get_member_details_service),
):
    try:
        employee = await department_service.assign_employee_department(
            current_user.id,
            organization_id,
            user_id,
            request.department_id,
        )
    except Exception as exc:
        _map_department_error(exc)

    profile = await member_details_service.get_profile(employee.user.id)
    onboarded = await member_details_service.is_onboarded(employee.user.id)
    if onboarded and employee.roles and OrgRole.MEMBER in employee.roles:
        completed_all_forms = await member_details_service.has_completed_all_forms(
            employee.user.id, organization_id=organization_id
        )
    else:
        completed_all_forms = False
    status_val = determine_employee_status(
        employee.roles, onboarded, completed_all_forms
    )

    return OrganizationEmployeeResponse(
        id=employee.user.id,
        email=employee.user.email,
        first_name=profile.first_name if profile and profile.first_name else None,
        last_name=profile.last_name if profile and profile.last_name else None,
        avatar_url=profile.avatar_url if profile else None,
        roles=[r.value for r in employee.roles],
        status=status_val,
        department=(
            DepartmentResponse(
                id=employee.department.id,
                organization_id=employee.department.organization_id,
                name=employee.department.name,
                slug=employee.department.slug,
            )
            if employee.department
            else None
        ),
    )


@router.patch(
    "/{organization_id}/employees/{user_id}/roles",
    response_model=OrganizationEmployeeResponse,
)
async def update_employee_roles(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    request: UpdateEmployeeRolesRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    use_case: UpdateEmployeeRolesUseCase = Depends(get_update_employee_roles_use_case),
    member_details_service: MemberDetailsService = Depends(get_member_details_service),
):
    try:
        employee = await use_case.execute(
            actor_user_id=current_user.id,
            actor_is_superuser=current_user.is_superuser,
            organization_id=organization_id,
            target_user_id=user_id,
            new_roles=request.roles,
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except MembershipNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="membership_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )
    except InsufficientRolePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except CannotRemoveOwnSuperadminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cannot_remove_own_superadmin",
        )
    except CannotRemoveLastSuperadminError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cannot_remove_last_superadmin",
        )

    profile = await member_details_service.get_profile(employee.user.id)
    onboarded = await member_details_service.is_onboarded(employee.user.id)
    if onboarded and employee.roles and OrgRole.MEMBER in employee.roles:
        completed_all_forms = await member_details_service.has_completed_all_forms(
            employee.user.id, organization_id=organization_id
        )
    else:
        completed_all_forms = False
    status_val = determine_employee_status(
        employee.roles, onboarded, completed_all_forms
    )

    return OrganizationEmployeeResponse(
        id=employee.user.id,
        email=employee.user.email,
        first_name=profile.first_name if profile and profile.first_name else None,
        last_name=profile.last_name if profile and profile.last_name else None,
        avatar_url=profile.avatar_url if profile else None,
        roles=[r.value for r in employee.roles],
        status=status_val,
        department=(
            DepartmentResponse(
                id=employee.department.id,
                organization_id=employee.department.organization_id,
                name=employee.department.name,
                slug=employee.department.slug,
            )
            if employee.department
            else None
        ),
    )


@router.delete(
    "/{organization_id}/employees/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_employee(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    use_case: UpdateEmployeeRolesUseCase = Depends(get_update_employee_roles_use_case),
):
    try:
        await use_case.execute(
            actor_user_id=current_user.id,
            actor_is_superuser=current_user.is_superuser,
            organization_id=organization_id,
            target_user_id=user_id,
            new_roles=[],
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except MembershipNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="membership_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )
    except InsufficientRolePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except CannotRemoveOwnSuperadminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cannot_remove_own_superadmin",
        )
    except CannotRemoveLastSuperadminError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cannot_remove_last_superadmin",
        )


@router.get(
    "/{organization_id}/employees", response_model=list[OrganizationEmployeeResponse]
)
async def list_organization_employees(
    organization_id: uuid.UUID,
    response: Response,
    role: list[OrgRole] | None = Query(default=None),
    department_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    score_filter: ScoreFilter | None = Query(default=None, alias="score"),
    search: str | None = Query(default=None),
    membership: MembershipState = Query(
        default=MembershipState.ALL,
        description="active: users with at least one role; "
        "inactive: deactivated users without roles; all: both.",
    ),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    use_case: ListOrganizationEmployeesUseCase = Depends(
        get_list_organization_employees_use_case
    ),
):
    try:
        employees, total = await use_case.execute(
            actor_user_id=current_user.id,
            organization_id=organization_id,
            roles=role,
            state=membership,
            department_id=department_id,
            status=status_filter,
            score_filter=score_filter,
            search=search,
            page=page,
            page_size=page_size,
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Page"] = str(page or 1)
    return [_to_organization_employee_response(employee) for employee in employees]


def _to_organization_employee_response(
    employee: EmployeeSummary,
) -> OrganizationEmployeeResponse:
    department = employee.department
    return OrganizationEmployeeResponse(
        id=employee.user_id,
        email=employee.email,
        first_name=employee.first_name,
        last_name=employee.last_name,
        avatar_url=employee.avatar_url,
        roles=[role.value for role in employee.roles],
        status=employee.status,
        department=(
            DepartmentResponse(
                id=department.id,
                organization_id=department.organization_id,
                name=department.name,
                slug=department.slug,
            )
            if department
            else None
        ),
        last_assessment=employee.last_assessment,
        overall_health_index=employee.overall_health_index,
    )


@router.get(
    "/{organization_id}/employees/{user_id}",
    response_model=EmployeeDetailResponse,
)
async def get_employee_detail(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    use_case: GetEmployeeDetailUseCase = Depends(get_employee_detail_use_case),
):
    try:
        detail = await use_case.execute(
            actor_user_id=current_user.id,
            actor_is_superuser=current_user.is_superuser,
            organization_id=organization_id,
            target_user_id=user_id,
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )
    except MembershipNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="membership_not_found",
        )
    return _to_employee_detail_response(detail)


def _to_employee_detail_response(detail: EmployeeDetailDTO) -> EmployeeDetailResponse:
    employee = detail.employee
    profile = detail.profile
    department = employee.department
    return EmployeeDetailResponse(
        id=employee.user.id,
        email=employee.user.email,
        first_name=profile.first_name or None if profile else None,
        last_name=profile.last_name or None if profile else None,
        avatar_url=profile.avatar_url if profile else None,
        phone_number=profile.phone_number if profile else None,
        date_of_birth=profile.date_of_birth if profile else None,
        roles=[role.value for role in employee.roles],
        status=detail.status,
        department=(
            DepartmentResponse(
                id=department.id,
                organization_id=department.organization_id,
                name=department.name,
                slug=department.slug,
            )
            if department
            else None
        ),
    )


async def _ensure_employee_access(
    current_user: AuthenticatedUser,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    membership_service: MembershipService,
) -> None:
    if current_user.is_superuser:
        return
    employees = await membership_service.list_employees_for_organization_admin(
        current_user.id, organization_id
    )
    if not any(employee.user.id == user_id for employee in employees):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")


@router.get(
    "/{organization_id}/employees/{user_id}/assessments",
    response_model=AssessmentsResponse,
)
async def get_employee_assessments(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    membership_service: MembershipService = Depends(get_membership_service),
    assessments_use_case: GetAssessmentsUseCase = Depends(get_get_assessments_use_case),
    organization_service: OrganizationService = Depends(get_organization_service),
    member_overall_score_repo: MemberOverallScoreRepository = Depends(
        get_member_overall_score_repository
    ),
) -> AssessmentsResponse:
    try:
        await _ensure_employee_access(
            current_user, organization_id, user_id, membership_service
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )

    results = await assessments_use_case.execute(user_id=user_id)

    response_results = [
        AssessmentResultResponse(
            score_id=str(res.id),
            score_name=_format_score_display_name(res.score_name),
            risk_level=res.risk_level,
            raw_value=res.raw_value,
            health_index=res.health_index,
            explanation=res.explanation,
            contributing_factors=res.contributing_factors,
            attention_flags=res.attention_flags,
            evaluated_at=res.evaluated_at,
        )
        for res in results
    ]

    (
        score_weights,
        risk_thresholds,
    ) = await organization_service.get_score_weights_and_thresholds(organization_id)
    latest_overall = await member_overall_score_repo.get_latest_by_user_id(user_id)
    persisted_history = await member_overall_score_repo.get_history_by_user_id(user_id)
    return build_assessments_response(
        response_results,
        page=page,
        limit=limit,
        score_weights=score_weights,
        risk_thresholds=risk_thresholds,
        latest_overall=latest_overall,
        persisted_history=persisted_history,
        active_scores_only=True,
    )


@router.get(
    "/{organization_id}/employees/{user_id}/assessment-submissions",
    response_model=AssessmentSubmissionListResponse,
)
async def list_employee_assessment_submissions(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    membership_service: MembershipService = Depends(get_membership_service),
    use_case: GetAssessmentSubmissionsUseCase = Depends(
        get_assessment_submissions_use_case
    ),
):
    try:
        await _ensure_employee_access(
            current_user, organization_id, user_id, membership_service
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="organization_not_found"
        )
    except NotOrganizationAdminError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    items, total = await use_case.list_for_employee(
        organization_id, user_id, page, limit
    )
    return AssessmentSubmissionListResponse(
        items=[
            AssessmentSubmissionSummaryResponse.model_validate(
                item, from_attributes=True
            )
            for item in items
        ],
        page=page,
        limit=limit,
        total=total,
        has_next=page * limit < total,
    )


@router.get(
    "/{organization_id}/employees/{user_id}/assessment-submissions/{submission_id}",
    response_model=AssessmentSubmissionDetailResponse,
)
async def get_employee_assessment_submission(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    submission_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    membership_service: MembershipService = Depends(get_membership_service),
    use_case: GetAssessmentSubmissionsUseCase = Depends(
        get_assessment_submissions_use_case
    ),
):
    try:
        await _ensure_employee_access(
            current_user, organization_id, user_id, membership_service
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="organization_not_found"
        )
    except NotOrganizationAdminError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    result = await use_case.get_detail(submission_id)
    if (
        result is None
        or result[0].user_id != user_id
        or result[0].organization_id != organization_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return _submission_detail_response(*result)


@router.get("/{organization_id}/score-weights", response_model=ScoreWeightsResponse)
async def get_organization_score_weights(
    organization_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    organization_service: OrganizationService = Depends(get_organization_service),
    membership_service: MembershipService = Depends(get_membership_service),
):
    try:
        if not current_user.is_superuser:
            await membership_service.list_employees_for_organization_admin(
                current_user.id, organization_id
            )
        (
            weights,
            thresholds,
        ) = await organization_service.get_score_weights_and_thresholds(organization_id)
        return ScoreWeightsResponse(
            score_weights=weights,
            risk_thresholds=thresholds,
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )


@router.get(
    "/{organization_id}/content-categories",
    response_model=list[ContentCategoryResponse],
)
async def list_organization_content_categories(
    organization_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    use_case: GetOrganizationContentCategoriesUseCase = Depends(
        get_organization_content_categories_use_case
    ),
):
    """Health topics content can be tagged with, flagging the enabled ones."""
    try:
        categories = await use_case.execute(
            actor_user_id=current_user.id,
            actor_is_superuser=current_user.is_superuser,
            organization_id=organization_id,
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )
    except HealthTopicsUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="health_topics_unavailable",
        )
    return [
        ContentCategoryResponse(
            key=category.key, label=category.label, active=category.active
        )
        for category in categories
    ]


@router.put("/{organization_id}/score-weights", response_model=ScoreWeightsResponse)
async def update_organization_score_weights(
    organization_id: uuid.UUID,
    request: ScoreWeightsRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    organization_service: OrganizationService = Depends(get_organization_service),
    membership_service: MembershipService = Depends(get_membership_service),
    recalculate_scores_use_case: RecalculateOrganizationOverallScoresUseCase = Depends(
        get_recalculate_org_scores_use_case
    ),
):
    try:
        if not current_user.is_superuser:
            await membership_service.list_employees_for_organization_admin(
                current_user.id, organization_id
            )
        updated_org = await organization_service.update_score_weights(
            organization_id,
            request.score_weights,
            risk_thresholds=request.risk_thresholds,
            changed_by_user_id=current_user.id,
        )

        # Recalculate immediately for all organization members within active session
        await recalculate_scores_use_case.execute(organization_id=organization_id)

        effective_thresholds = (
            updated_org.risk_thresholds
            if updated_org.risk_thresholds is not None
            else request.risk_thresholds
        )

        return ScoreWeightsResponse(
            score_weights=updated_org.score_weights or request.score_weights,
            risk_thresholds=effective_thresholds,
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{organization_id}/analytics/trends",
    response_model=list[RiskTrendPointResponse],
)
async def get_organization_risk_trends(
    organization_id: uuid.UUID,
    months: int = Query(12, ge=1, le=36),
    department_id: uuid.UUID | None = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    analytics_use_case: GetOrganizationAnalyticsUseCase = Depends(
        get_organization_analytics_use_case
    ),
    membership_service: MembershipService = Depends(get_membership_service),
) -> list[RiskTrendPointResponse]:
    try:
        if not current_user.is_superuser:
            await membership_service.list_employees_for_organization_admin(
                current_user.id, organization_id
            )
        points = await analytics_use_case.get_trends(
            organization_id=organization_id,
            months=months,
            department_id=department_id,
        )
        return [
            RiskTrendPointResponse(
                period=p.period,
                month_label=p.month_label,
                average_score=p.average_score,
                total_assessments=p.total_assessments,
                scores_by_study={
                    _format_score_display_name(k): v
                    for k, v in p.scores_by_study.items()
                },
            )
            for p in points
        ]
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )


@router.get(
    "/{organization_id}/analytics/departments",
    response_model=list[DepartmentAnalyticsSummaryResponse],
)
async def get_organization_department_analytics(
    organization_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    analytics_use_case: GetOrganizationAnalyticsUseCase = Depends(
        get_organization_analytics_use_case
    ),
    membership_service: MembershipService = Depends(get_membership_service),
) -> list[DepartmentAnalyticsSummaryResponse]:
    try:
        if not current_user.is_superuser:
            await membership_service.list_employees_for_organization_admin(
                current_user.id, organization_id
            )
        summaries = await analytics_use_case.get_departments_summary(organization_id)
        return [
            DepartmentAnalyticsSummaryResponse(
                department_id=s.department_id,
                name=s.name,
                average_score=s.average_score,
                total_workers=s.total_workers,
                high_risk_count=s.high_risk_count,
            )
            for s in summaries
        ]
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )


@router.get(
    "/{organization_id}/registration-trends",
    response_model=list[RegistrationTrendPointResponse],
)
async def get_organization_registration_trends(
    organization_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    analytics_use_case: GetOrganizationAnalyticsUseCase = Depends(
        get_organization_analytics_use_case
    ),
    membership_service: MembershipService = Depends(get_membership_service),
) -> list[RegistrationTrendPointResponse]:
    try:
        if not current_user.is_superuser:
            await membership_service.list_employees_for_organization_admin(
                current_user.id, organization_id
            )
        points = await analytics_use_case.get_registration_trends(organization_id)
        return [
            RegistrationTrendPointResponse(
                period=p.period,
                date_label=p.date_label,
                new_members=p.new_members,
                cumulative_members=p.cumulative_members,
            )
            for p in points
        ]
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )


@router.get(
    "/{organization_id}/audit-logs",
    response_model=AuditLogListResponse,
)
async def get_organization_audit_logs(
    organization_id: uuid.UUID,
    action: str | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    use_case: GetOrganizationAuditLogsUseCase = Depends(
        get_get_organization_audit_logs_use_case
    ),
    membership_service: MembershipService = Depends(get_membership_service),
) -> AuditLogListResponse:
    try:
        if not current_user.is_superuser:
            await membership_service.list_employees_for_organization_admin(
                current_user.id, organization_id
            )
        result = await use_case.execute(
            organization_id=organization_id,
            action=action,
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
        return AuditLogListResponse(
            items=[
                AuditLogItemResponse(
                    id=item.id,
                    user_id=item.user_id,
                    user_email=item.user_email,
                    user_name=item.user_name,
                    organization_id=item.organization_id,
                    action=item.action,
                    resource_type=item.resource_type,
                    resource_id=item.resource_id,
                    details=item.details,
                    created_at=item.created_at,
                )
                for item in result.items
            ],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            has_next=result.has_next,
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )


@router.get(
    "/{organization_id}/compliance-summary",
    response_model=ConsentComplianceSummaryResponse,
)
async def get_organization_compliance_summary(
    organization_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    use_case: GetOrganizationComplianceSummaryUseCase = Depends(
        get_get_organization_compliance_summary_use_case
    ),
    membership_service: MembershipService = Depends(get_membership_service),
) -> ConsentComplianceSummaryResponse:
    try:
        if not current_user.is_superuser:
            await membership_service.list_employees_for_organization_admin(
                current_user.id, organization_id
            )
        summary = await use_case.execute(organization_id=organization_id)
        return ConsentComplianceSummaryResponse(
            total_audit_events=summary.total_audit_events,
            consent_accepted_count=summary.consent_accepted_count,
            consent_revoked_count=summary.consent_revoked_count,
            data_exported_count=summary.data_exported_count,
            audited_members_count=summary.audited_members_count,
            actions_breakdown=summary.actions_breakdown,
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )
