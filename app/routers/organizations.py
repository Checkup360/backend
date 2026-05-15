import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.exc import IntegrityError

from app.auth.authorization import require_superuser
from app.models import User
from app.repositories.organization import (
    OrganizationRepository,
    get_organization_repository,
)

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
    repo: OrganizationRepository = Depends(get_organization_repository),
    current_user: User = Depends(require_superuser),
):
    return await repo.list()


@router.post(
    "/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED
)
async def create_organization(
    request: CreateOrganizationRequest,
    repo: OrganizationRepository = Depends(get_organization_repository),
    current_user: User = Depends(require_superuser),
):
    existing_organization = await repo.get_by_slug(request.slug)
    if existing_organization:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="organization_slug_already_exists",
        )

    try:
        organization = await repo.create(name=request.name, slug=request.slug)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="organization_slug_already_exists",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="unknown_error",
        )

    return organization
