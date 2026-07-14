from fastapi import Depends, HTTPException, status

from app.application.dto import AuthenticatedUser
from app.domain.entities import Membership, OrgRole
from app.presentation.api.dependencies import (
    get_current_user,
    get_member_details_service,
    get_membership_service,
)
from app.application.use_cases.members.member_details_service import (
    MemberDetailsService,
)
from app.application.use_cases.memberships.membership_service import MembershipService


def require_superuser(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return current_user


async def _validate_organization_admin(
    current_user: AuthenticatedUser,
) -> Membership:
    if not current_user.membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    if OrgRole.ADMIN not in current_user.membership.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    return current_user.membership


async def require_org_admin_any(
    membership_service: MembershipService = Depends(get_membership_service),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if await membership_service.is_admin_of_any(current_user.id):
        return current_user

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


async def require_completed_member_onboarding(
    member_details_service: MemberDetailsService = Depends(get_member_details_service),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if await member_details_service.requires_onboarding(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="onboarding_required",
        )

    return current_user


async def require_organization_admin(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Membership:
    return await _validate_organization_admin(current_user)


async def require_organization_admin_or_sysadmin(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Membership | AuthenticatedUser:
    if current_user.is_superuser:
        return current_user

    return await _validate_organization_admin(current_user)
