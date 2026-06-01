import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator

from app.auth.authorization import require_superuser
from app.auth.machinery.users import current_active_user
from app.dependencies import get_membership_service, get_organization_service
from app.domain.entities.org_role import OrgRole
from app.domain.exceptions import (
    NotOrganizationAdminError,
    OrganizationNotFoundError,
    OrganizationSlugAlreadyExists,
)
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


class OrganizationEmployeeResponse(BaseModel):
    id: uuid.UUID
    email: str
    roles: list[str]


@router.get("/", response_model=list[OrganizationResponse])
async def list_organizations(
    service: OrganizationService = Depends(get_organization_service),
    current_user: User = Depends(require_superuser),
):
    return await service.list_organizations()


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


@router.get(
    "/{organization_id}/employees", response_model=list[OrganizationEmployeeResponse]
)
async def list_organization_employees(
    organization_id: uuid.UUID,
    role: list[OrgRole] | None = Query(default=None),
    current_user: User = Depends(current_active_user),
    membership_service: MembershipService = Depends(get_membership_service),
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

    return [
        OrganizationEmployeeResponse(
            id=employee.user.id,
            email=employee.user.email,
            roles=[r.value for r in employee.roles],
        )
        for employee in employees
    ]
