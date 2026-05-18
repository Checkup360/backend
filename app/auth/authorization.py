import uuid

from fastapi import Depends, HTTPException, Request, status

from app.auth.machinery.users import current_active_user
from app.domain.entities import Membership
from app.models import User
from app.domain.services.membership import MembershipService, get_membership_service


def require_superuser(
    current_user: User = Depends(current_active_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return current_user


async def _validate_organization_admin(
    request: Request,
    membership_service: MembershipService,
    current_user: User,
) -> Membership:
    body = await request.json()
    organization_id = body.get("organization_id")
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="organization_id_required",
        )

    try:
        organization_uuid = uuid.UUID(str(organization_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid_organization_id",
        )

    organization = await membership_service.org_repo.get(organization_uuid)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )

    membership = await membership_service.get_admin_membership(
        current_user.id, organization_uuid
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    return membership


async def require_org_admin_any(
    membership_service: MembershipService = Depends(get_membership_service),
    current_user: User = Depends(current_active_user),
) -> User:
    if await membership_service.is_admin_of_any(current_user.id):
        return current_user

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


async def require_organization_admin(
    request: Request,
    membership_service: MembershipService = Depends(get_membership_service),
    current_user: User = Depends(current_active_user),
) -> Membership:
    return await _validate_organization_admin(request, membership_service, current_user)


async def require_organization_admin_or_sysadmin(
    request: Request,
    membership_service: MembershipService = Depends(get_membership_service),
    current_user: User = Depends(current_active_user),
) -> Membership | User:
    if current_user.is_superuser:
        return current_user

    return await _validate_organization_admin(request, membership_service, current_user)
