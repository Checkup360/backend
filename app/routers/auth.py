from fastapi import APIRouter

from app.auth.backend import auth_backend
from app.auth.google_oauth import google_oauth_client
from app.auth.users import fastapi_users
from app.core import settings

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
    ),
    prefix="/google",
)
