import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, field_validator

from app.auth.authorization import require_superuser
from app.auth.machinery.users import current_active_user
from app.dependencies import (
    get_department_service,
    get_membership_service,
    get_organization_service,
    get_member_details_repository,
)
from app.persistence.repositories.member_details import MemberDetailsRepository
from app.domain.entities.org_role import OrgRole
from app.domain.exceptions import (
    DepartmentInUseError,
    DepartmentNotFoundError,
    DepartmentSlugAlreadyExists,
    NotOrganizationAdminError,
    OrganizationNotFoundError,
    OrganizationSlugAlreadyExists,
)
from app.domain.services.department import DepartmentService
from app.domain.services.membership import MembershipService
from app.persistence.models import User
from app.domain.services.organization import OrganizationService

router = APIRouter(prefix="/organizations", tags=["orgs"])


class CreateOrganizationRequest(BaseModel):
    name: str
    slug: str

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("slug_required")
        v = v.strip()
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("invalid_slug_format")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name_required")
        return v.strip()


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    collaborators_count: int


class OrganizationSummaryResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    total_members: int
    total_employees: int
    total_admins: int


class DepartmentRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_department_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("department_name_required")
        return v.strip()


class AssignDepartmentRequest(BaseModel):
    department_id: uuid.UUID | None = None


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str


class OrganizationEmployeeResponse(BaseModel):
    id: uuid.UUID
    email: str
    roles: list[str]
    status: str
    department: DepartmentResponse | None = None


@router.get("/", response_model=list[OrganizationResponse])
async def list_organizations(
    response: Response,
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    service: OrganizationService = Depends(get_organization_service),
    current_user: User = Depends(require_superuser),
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
    current_user: User = Depends(require_superuser),
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
    _: User = Depends(require_superuser),
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

    return OrganizationSummaryResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        total_members=total_members,
        total_employees=total_employees,
        total_admins=total_admins,
    )


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: uuid.UUID,
    service: OrganizationService = Depends(get_organization_service),
    _: User = Depends(require_superuser),
):
    deleted = await service.delete_organization(id=organization_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )


def _map_department_error(exc: Exception):
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
    current_user: User = Depends(current_active_user),
    department_service: DepartmentService = Depends(get_department_service),
):
    try:
        if current_user.is_superuser:
            return await department_service.list_departments_as_superuser(
                organization_id
            )
        return await department_service.list_departments(
            current_user.id, organization_id
        )
    except Exception as exc:
        _map_department_error(exc)


@router.post(
    "/{organization_id}/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_department(
    organization_id: uuid.UUID,
    request: DepartmentRequest,
    current_user: User = Depends(current_active_user),
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
    current_user: User = Depends(current_active_user),
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
    current_user: User = Depends(current_active_user),
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
    current_user: User = Depends(current_active_user),
    department_service: DepartmentService = Depends(get_department_service),
    member_details_repo: MemberDetailsRepository = Depends(
        get_member_details_repository
    ),
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

    onboarded = await member_details_repo.exists_for_user(employee.user.id)
    status_val = "active" if onboarded else "onboarding"

    return OrganizationEmployeeResponse(
        id=employee.user.id,
        email=employee.user.email,
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
    current_user: User = Depends(current_active_user),
    membership_service: MembershipService = Depends(get_membership_service),
    member_details_repo: MemberDetailsRepository = Depends(
        get_member_details_repository
    ),
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
        onboarded = await member_details_repo.exists_for_user(employee.user.id)
        status_val = "active" if onboarded else "onboarding"

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
