import uuid

from fastapi import Depends, HTTPException, Request, status

from app.auth.users import current_active_user
from app.models import Membership, User
from app.models.membership import OrgRole
from app.repositories.membership import (
    MembershipRepository,
    get_membership_repository,
)
from app.repositories.organization import (
    OrganizationRepository,
    get_organization_repository,
)


def require_superuser(
    current_user: User = Depends(current_active_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return current_user


async def _validate_organization_admin(
    request: Request,
    org_repo: OrganizationRepository,
    membership_repo: MembershipRepository,
    current_user: User,
) -> Membership:
    """
    Helper function to validate if current_user is an admin of the organization
    specified in the request body.
    """
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

    organization = await org_repo.get(organization_uuid)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )

    membership = await membership_repo.get_by_user_and_org(
        current_user.id, organization_uuid
    )
    if not membership or membership.role != OrgRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    return membership


async def require_org_admin_any(
    membership_repo: MembershipRepository = Depends(get_membership_repository),
    current_user: User = Depends(current_active_user),
) -> User:
    if await membership_repo.is_admin_of_any(current_user.id):
        return current_user

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


async def require_organization_admin(
    request: Request,
    org_repo: OrganizationRepository = Depends(get_organization_repository),
    membership_repo: MembershipRepository = Depends(get_membership_repository),
    current_user: User = Depends(current_active_user),
) -> Membership:
    return await _validate_organization_admin(
        request, org_repo, membership_repo, current_user
    )


async def require_organization_admin_or_sysadmin(
    request: Request,
    org_repo: OrganizationRepository = Depends(get_organization_repository),
    membership_repo: MembershipRepository = Depends(get_membership_repository),
    current_user: User = Depends(current_active_user),
) -> Membership | User:
    """
    Allows either a sysadmin or an organization admin to proceed.
    - Sysadmin: can create invites for any organization
    - Org admin: can create invites only for their organization
    """
    if current_user.is_superuser:
        return current_user

    return await _validate_organization_admin(
        request, org_repo, membership_repo, current_user
    )
