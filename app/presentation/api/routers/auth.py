from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi_users.authentication import JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase

from app.infrastructure.authentication.dependencies import (
    get_refresh_token_service,
    get_user_db,
)
from app.infrastructure.authentication.machinery.backend import (
    auth_backend,
    cookie_transport,
)
from app.domain.services.refresh_token_service import RefreshTokenService
from app.infrastructure.authentication.machinery.google_oauth import google_oauth_client
from app.infrastructure.authentication.machinery.users import (
    fastapi_users,
)
from app.application.dto import AuthenticatedUser
from app.infrastructure.config import settings
from app.presentation.api.authorization import require_superuser
from app.presentation.api.dependencies import get_member_details_service
from app.application.use_cases.members.member_details_service import (
    MemberDetailsService,
)
from app.presentation.api.dependencies import get_current_user
from app.presentation.api.response_models import AuthMeResponse, OrganizationMembership

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_token(
    request: Request,
    refresh_token_service: RefreshTokenService = Depends(get_refresh_token_service),
    strategy: JWTStrategy = Depends(auth_backend.get_strategy),
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
):
    raw_token = request.cookies.get(settings.refresh_token_cookie_name)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    try:
        user_id, new_raw_token, _ = await refresh_token_service.validate_and_rotate(
            raw_token
        )
    except ValueError as e:
        logout_resp = Response(status_code=status.HTTP_401_UNAUTHORIZED)
        cookie_transport._set_logout_cookie(logout_resp)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers=dict(logout_resp.headers),
        )

    user = await user_db.get(user_id)
    if not user or not user.is_active:
        logout_resp = Response(status_code=status.HTTP_401_UNAUTHORIZED)
        cookie_transport._set_logout_cookie(logout_resp)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers=dict(logout_resp.headers),
        )

    new_access_token = await strategy.write_token(user)
    response = Response(
        content='{"ok":true}',
        status_code=status.HTTP_200_OK,
        media_type="application/json",
    )
    cookie_transport._set_login_cookie(response, new_access_token)
    cookie_transport._set_refresh_cookie(response, new_raw_token)

    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    refresh_token_service: RefreshTokenService = Depends(get_refresh_token_service),
):
    raw_token = request.cookies.get(settings.refresh_token_cookie_name)
    if raw_token:
        await refresh_token_service.revoke_token(raw_token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    cookie_transport._set_logout_cookie(response)
    return response


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
            organization_logo_url=user.organization_logo_url,
            roles=[r.value for r in user.membership.roles],
        )
    profile = await member_details_service.get_profile(user.id)
    return AuthMeResponse(
        email=user.email,
        first_name=profile.first_name if profile and profile.first_name else None,
        last_name=profile.last_name if profile and profile.last_name else None,
        avatar_url=profile.avatar_url if profile else None,
        is_sysadmin=user.is_superuser,
        membership=membership,
        requires_onboarding=await member_details_service.requires_onboarding(user),
    )


@router.get("/verify-sysadmin", status_code=status.HTTP_200_OK)
async def verify_sysadmin(
    response: Response,
    current_user: AuthenticatedUser = Depends(require_superuser),
):
    """
    Endpoint used by Caddy forward_auth to verify that the request comes
    from an authenticated sysadmin. Sets identity headers.
    """
    response.headers["Remote-User"] = current_user.email
    response.headers["Remote-Email"] = current_user.email
    return Response(
        status_code=status.HTTP_200_OK,
        headers={
            "Remote-User": current_user.email,
            "Remote-Email": current_user.email,
        },
    )
