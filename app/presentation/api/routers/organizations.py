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
    get_risk_score_repository,
)
from app.application.use_cases.organizations import (
    DeleteOrganizationLogoUseCase,
    GetOrganizationAnalyticsUseCase,
    UploadOrganizationLogoUseCase,
)
from app.presentation.api.response_models.analytics import (
    DepartmentAnalyticsSummaryResponse,
    RegistrationTrendPointResponse,
    RiskTrendPointResponse,
)
from app.domain.value_objects.org_role import OrgRole
from app.domain.exceptions import (
    DepartmentInUseError,
    DepartmentNotFoundError,
    DepartmentSlugAlreadyExists,
    NotOrganizationAdminError,
    OrganizationNotFoundError,
    OrganizationSlugAlreadyExists,
)
from app.application.use_cases.departments.department_service import DepartmentService
from app.application.use_cases.memberships.membership_service import MembershipService
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
from app.domain.repositories.risk_score import RiskScoreRepository
from app.presentation.api.request_models.organization import (
    AssignDepartmentRequest,
    CreateOrganizationRequest,
    DepartmentRequest,
    ScoreWeightsRequest,
    UpdateOrganizationRequest,
)
from app.presentation.api.response_models.organization import (
    DepartmentResponse,
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

router = APIRouter(prefix="/organizations", tags=["orgs"])


@router.get("/", response_model=list[OrganizationResponse])
async def list_organizations(
    response: Response,
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    service: OrganizationService = Depends(get_organization_service),
    current_user: AuthenticatedUser = Depends(require_superuser),
):
    orgs = await service.list_organizations()
    if status_filter is not None:
        status_filter_lower = status_filter.lower()
        res = []
        for org in orgs:
            org_status = "active" if org.collaborators_count > 0 else "pending"
            if org_status == status_filter_lower:
                res.append(org)
        orgs = res
    if search is not None and search.strip():
        search_lower = search.strip().lower()
        orgs = [
            org
            for org in orgs
            if search_lower in org.name.lower() or search_lower in org.slug.lower()
        ]
    total = len(orgs)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page-Size"] = str(page_size)
    if page is not None:
        response.headers["X-Page"] = str(page)
        start = (page - 1) * page_size
        return orgs[start : start + page_size]
    response.headers["X-Page"] = "1"
    return orgs


@router.post(
    "/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED
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
            departments = await department_service.list_departments_as_superuser(
                organization_id
            )
        else:
            departments = await department_service.list_departments(
                current_user.id, organization_id
            )
    except Exception as exc:
        _map_department_error(exc)

    if search is not None and search.strip():
        search_lower = search.strip().lower()
        departments = [
            d
            for d in departments
            if search_lower in d.name.lower() or search_lower in d.slug.lower()
        ]

    total = len(departments)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page-Size"] = str(page_size)
    if page is not None:
        response.headers["X-Page"] = str(page)
        start = (page - 1) * page_size
        return departments[start : start + page_size]
    response.headers["X-Page"] = "1"
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
    status_val = "active" if onboarded else "onboarding"

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


@router.get(
    "/{organization_id}/employees", response_model=list[OrganizationEmployeeResponse]
)
async def list_organization_employees(
    organization_id: uuid.UUID,
    response: Response,
    role: list[OrgRole] | None = Query(default=None),
    department_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    membership_service: MembershipService = Depends(get_membership_service),
    member_details_service: MemberDetailsService = Depends(get_member_details_service),
    risk_score_repository: RiskScoreRepository = Depends(get_risk_score_repository),
):
    try:
        employees = await membership_service.list_employees_for_organization_admin(
            current_user.id, organization_id, roles=role
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

    res = []
    for employee in employees:
        profile = await member_details_service.get_profile(employee.user.id)
        onboarded = await member_details_service.is_onboarded(employee.user.id)
        status_val = "active" if onboarded else "onboarding"
        employee_scores = await risk_score_repository.get_by_user_id(employee.user.id)
        last_assessment = max(
            (score.evaluated_at for score in employee_scores if score.evaluated_at),
            default=None,
        )

        # Apply department query parameter filter
        if department_id is not None:
            if not employee.department or employee.department.id != department_id:
                continue

        # Apply status query parameter filter
        if status_filter is not None:
            if status_val.lower() != status_filter.lower():
                continue

        if search is not None and search.strip():
            search_lower = search.strip().lower()
            department_name = (
                employee.department.name if employee.department else "Unassigned"
            )
            if (
                search_lower not in employee.user.email.lower()
                and search_lower not in department_name.lower()
            ):
                continue

        res.append(
            OrganizationEmployeeResponse(
                id=employee.user.id,
                email=employee.user.email,
                first_name=profile.first_name
                if profile and profile.first_name
                else None,
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
                last_assessment=last_assessment,
            )
        )
    total = len(res)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page-Size"] = str(page_size)
    if page is not None:
        response.headers["X-Page"] = str(page)
        start = (page - 1) * page_size
        return res[start : start + page_size]
    response.headers["X-Page"] = "1"
    return res


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
) -> AssessmentsResponse:
    try:
        if not current_user.is_superuser:
            await membership_service.list_employees_for_organization_admin(
                current_user.id, organization_id
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
            normalized_value=res.normalized_value,
            explanation=res.explanation,
            contributing_factors=res.contributing_factors,
            attention_flags=res.attention_flags,
            evaluated_at=res.evaluated_at,
        )
        for res in results
    ]

    score_weights = await organization_service.get_score_weights(organization_id)
    return build_assessments_response(
        response_results, page=page, limit=limit, score_weights=score_weights
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
        weights = await organization_service.get_score_weights(organization_id)
        return ScoreWeightsResponse(score_weights=weights)
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


@router.put("/{organization_id}/score-weights", response_model=ScoreWeightsResponse)
async def update_organization_score_weights(
    organization_id: uuid.UUID,
    request: ScoreWeightsRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    organization_service: OrganizationService = Depends(get_organization_service),
    membership_service: MembershipService = Depends(get_membership_service),
):
    try:
        if not current_user.is_superuser:
            await membership_service.list_employees_for_organization_admin(
                current_user.id, organization_id
            )
        updated_org = await organization_service.update_score_weights(
            organization_id, request.score_weights
        )
        return ScoreWeightsResponse(
            score_weights=updated_org.score_weights or request.score_weights
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
                risk_index=p.risk_index,
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
