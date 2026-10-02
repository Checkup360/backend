from fastapi import Depends, HTTPException, status

from app.application.dto import AuthenticatedUser
from app.domain.entities import Membership, OrgRole
from app.domain.entities.user_consent import ConsentType, UserConsent
from app.domain.repositories.user_consent import UserConsentRepository
from app.domain.services.form_registry import FormRegistry
from app.presentation.api.dependencies import (
    get_current_user,
    get_form_registry,
    get_member_details_service,
    get_membership_service,
    get_user_consent_repository,
)
from app.application.use_cases.members.member_details_service import (
    MemberDetailsService,
)
from app.application.use_cases.memberships.membership_service import MembershipService

_ADMIN_ROLES: frozenset[OrgRole] = frozenset({OrgRole.ADMIN, OrgRole.SUPERADMIN})
_CMS_ROLES: frozenset[OrgRole] = frozenset(
    {OrgRole.SUPERADMIN, OrgRole.ADMIN, OrgRole.CONTENT_MANAGER}
)


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

    if not _ADMIN_ROLES.intersection(current_user.membership.roles):
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


async def require_organization_superadmin(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Membership:
    if not current_user.membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    if OrgRole.SUPERADMIN not in current_user.membership.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    return current_user.membership


async def require_organization_superadmin_or_sysadmin(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Membership | AuthenticatedUser:
    if current_user.is_superuser:
        return current_user

    return await require_organization_superadmin(current_user)


async def require_member_role(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Ensures user has active member role. Rejects deactivated or non-member users."""
    if (
        current_user.membership is not None
        and OrgRole.MEMBER not in current_user.membership.roles
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    return current_user


async def require_active_member(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Ensures user has active organization membership with the member role."""
    if (
        not current_user.membership
        or OrgRole.MEMBER not in current_user.membership.roles
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    return current_user


async def require_content_manager_or_above(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Membership:
    """Allows org superadmins, admins and content managers. Rejects plain members and unauthenticated users."""
    if not current_user.membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    if not _CMS_ROLES.intersection(current_user.membership.roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    return current_user.membership


async def require_health_data_consent(
    current_user: AuthenticatedUser = Depends(get_current_user),
    consent_repo: UserConsentRepository = Depends(get_user_consent_repository),
) -> AuthenticatedUser:
    """Ensures user has active general health data processing consent."""
    consent = await consent_repo.get_active_consent(
        user_id=current_user.id,
        consent_type=ConsentType.HEALTH_DATA_PROCESSING_CONSENT,
    )
    if not consent or not consent.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="health_data_processing_consent_required",
        )
    return current_user


async def require_form_consent(
    form_type: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    consent_repo: UserConsentRepository = Depends(get_user_consent_repository),
    form_registry: FormRegistry = Depends(get_form_registry),
) -> UserConsent:
    """Ensures user has active general health consent AND specific form consent for the current version."""
    # 1. Verify Level 1 Health Data Processing consent
    health_consent = await consent_repo.get_active_consent(
        user_id=current_user.id,
        consent_type=ConsentType.HEALTH_DATA_PROCESSING_CONSENT,
    )
    if not health_consent or not health_consent.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="health_data_processing_consent_required",
        )

    # 2. Verify Level 2 specific form consent matching current form version
    form_consent = await consent_repo.get_active_consent(
        user_id=current_user.id,
        consent_type=ConsentType.FORM_CONSENT,
        form_type=form_type,
    )
    current_version = form_registry.get_form_version(form_type)
    if (
        not form_consent
        or not form_consent.is_active
        or not form_consent.matches_version(current_version)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"active_consent_required_for_form_{form_type}",
        )

    return form_consent


async def require_biometrics_consent(
    current_user: AuthenticatedUser = Depends(get_current_user),
    consent_repo: UserConsentRepository = Depends(get_user_consent_repository),
    form_registry: FormRegistry = Depends(get_form_registry),
) -> UserConsent:
    """Ensures user has active biometrics consent."""
    return await require_form_consent(
        form_type="biometrics",
        current_user=current_user,
        consent_repo=consent_repo,
        form_registry=form_registry,
    )
