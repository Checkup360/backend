from fastapi import APIRouter, Depends

from app.auth.machinery.backend import auth_backend
from app.auth.machinery.google_oauth import google_oauth_client
from app.auth.machinery.users import current_active_user, fastapi_users
from app.core import settings
from app.dependencies import get_member_details_service
from app.domain.services.member_details import MemberDetailsService
from app.persistence.models import User
from app.schemas.auth import AuthMeResponse, OrganizationMembership

router = APIRouter(prefix="/auth", tags=["auth"])

router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="",
)

router.include_router(
    fastapi_users.get_oauth_router(
        oauth_client=google_oauth_client,
        backend=auth_backend,
        state_secret=settings.auth_secret,
        associate_by_email=True,
        is_verified_by_default=True,
        csrf_token_cookie_secure=settings.cookie_secure,
    ),
    prefix="/google",
)


@router.get("/me", response_model=AuthMeResponse)
async def get_me(
    user: User = Depends(current_active_user),
    member_details_service: MemberDetailsService = Depends(get_member_details_service),
) -> AuthMeResponse:
    memberships = [
        OrganizationMembership(
            organization_id=m.organization_id,
            organization_name=m.organization.name,
            roles=[r.value for r in m.roles],
        )
        for m in user.memberships
    ]
    return AuthMeResponse(
        email=user.email,
        is_sysadmin=user.is_superuser,
        memberships=memberships,
        requires_onboarding=await member_details_service.requires_onboarding(user),
    )
