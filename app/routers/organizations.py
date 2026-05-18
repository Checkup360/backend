import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from app.auth.authorization import require_superuser
from app.dependencies import get_organization_service
from app.domain.exceptions import OrganizationSlugAlreadyExists
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
