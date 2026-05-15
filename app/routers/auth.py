from fastapi import APIRouter, Depends

from app.auth.machinery.backend import auth_backend
from app.auth.machinery.google_oauth import google_oauth_client
from app.auth.machinery.users import current_active_user, fastapi_users
from app.core import settings
from app.models import User
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
def get_me(user: User = Depends(current_active_user)) -> AuthMeResponse:
    memberships = [
        OrganizationMembership(
            organization_id=m.organization_id,
            organization_name=m.organization.name,
            role=m.role.value,
        )
        for m in user.memberships
    ]
    return AuthMeResponse(
        email=user.email,
        is_sysadmin=user.is_superuser,
        memberships=memberships,
    )
