from fastapi import APIRouter, Depends

from app.infrastructure.authentication.machinery.backend import auth_backend
from app.infrastructure.authentication.machinery.google_oauth import google_oauth_client
from app.infrastructure.authentication.machinery.users import (
    fastapi_users,
)
from app.application.dto import AuthenticatedUser
from app.infrastructure.config import settings
from app.presentation.api.dependencies import get_member_details_service
from app.application.use_cases.members.member_details_service import (
    MemberDetailsService,
)
from app.presentation.api.dependencies import get_current_user
from app.presentation.api.response_models import AuthMeResponse, OrganizationMembership

router = APIRouter(prefix="/auth", tags=["auth"])

router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="",
)

router.include_router(
    fastapi_users.get_reset_password_router(),
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
    user: AuthenticatedUser = Depends(get_current_user),
    member_details_service: MemberDetailsService = Depends(get_member_details_service),
) -> AuthMeResponse:
    membership = None
    if user.membership:
        membership = OrganizationMembership(
            organization_id=user.membership.organization_id,
            organization_name=user.organization_name or "",
            roles=[r.value for r in user.membership.roles],
        )
    return AuthMeResponse(
        email=user.email,
        is_sysadmin=user.is_superuser,
        membership=membership,
        requires_onboarding=await member_details_service.requires_onboarding(user),
    )
