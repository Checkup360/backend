from fastapi import Depends, HTTPException, status

from app.auth.machinery.users import current_active_user
from app.domain.entities import Membership, OrgRole
from app.persistence.models import User
from app.dependencies import get_member_details_service, get_membership_service
from app.domain.services.member_details import MemberDetailsService
from app.domain.services.membership import MembershipService


def require_superuser(
    current_user: User = Depends(current_active_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return current_user


async def _validate_organization_admin(
    current_user: User,
) -> Membership:
    if not current_user.membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    if OrgRole.ADMIN not in current_user.membership.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    return current_user.membership


async def require_org_admin_any(
    membership_service: MembershipService = Depends(get_membership_service),
    current_user: User = Depends(current_active_user),
) -> User:
    if await membership_service.is_admin_of_any(current_user.id):
        return current_user

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


async def require_completed_member_onboarding(
    member_details_service: MemberDetailsService = Depends(get_member_details_service),
    current_user: User = Depends(current_active_user),
) -> User:
    if await member_details_service.requires_onboarding(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="onboarding_required",
        )

    return current_user


async def require_organization_admin(
    current_user: User = Depends(current_active_user),
) -> Membership:
    return await _validate_organization_admin(current_user)


async def require_organization_admin_or_sysadmin(
    current_user: User = Depends(current_active_user),
) -> Membership | User:
    if current_user.is_superuser:
        return current_user

    return await _validate_organization_admin(current_user)
