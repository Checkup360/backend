import uuid
from typing import NoReturn, Optional

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi_users import BaseUserManager, UUIDIDMixin, exceptions
from fastapi_users.db import SQLAlchemyUserDatabase

from app.application.use_cases.authentication import RequestPasswordReset, ResetPassword
from app.infrastructure.authentication.dependencies import (
    get_invite_service_for_auth,
    get_smtp_email_sender,
    get_user_db,
)
from app.infrastructure.config import settings
from app.infrastructure.authentication.machinery.cookies import (
    clear_pending_invite_cookie,
)
from app.domain.entities import InviteToken
from app.domain.exceptions import (
    InviteError,
    InviteExhaustedError,
    InviteNotFoundError,
    UserNotFoundError,
)
from app.infrastructure.persistence.models import User
from app.domain.services.invite import InviteService
from app.infrastructure.email import SmtpEmailSender


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.auth_secret
    verification_token_secret = settings.auth_secret

    def __init__(
        self,
        user_db,
        invite_service: InviteService,
        request_password_reset: RequestPasswordReset | None = None,
        reset_password: ResetPassword | None = None,
    ):
        super().__init__(user_db)
        self.invite_service = invite_service
        self.request_password_reset = request_password_reset
        self.password_reset_policy = reset_password

    async def validate_password(self, password: str, user) -> None:
        if self.password_reset_policy is None:
            return
        policy_error = self.password_reset_policy.get_validation_error(password)
        if policy_error:
            raise exceptions.InvalidPasswordException(reason=policy_error)

    async def on_after_forgot_password(
        self,
        user: User,
        token: str,
        request: Optional[Request] = None,
    ) -> None:
        if self.request_password_reset is not None:
            await self.request_password_reset.execute(user.email, token)

    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
        response: Optional[Response] = None,
    ) -> None:
        if not request or not response:
            return

        if hasattr(request.state, "invite_pending_consumption_id"):
            pending_id = getattr(request.state, "invite_pending_consumption_id", None)
            if pending_id:
                await self._consume_invite_by_id(pending_id, user)
                request.state.invite_pending_consumption_id = None

        if request.cookies.get("pending_invite"):
            clear_pending_invite_cookie(response)

    async def oauth_callback(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        oauth_name: str,
        access_token: str,
        account_id: str,
        account_email: str,
        expires_at: int | None = None,
        refresh_token: str | None = None,
        request: Optional[Request] = None,
        *,
        associate_by_email: bool = False,
        is_verified_by_default: bool = False,
    ) -> User:
        existing_user = await self.user_db.get_by_oauth_account(oauth_name, account_id)

        if existing_user:
            if request and self._has_invite_token(request):
                invite = await self._assert_invite_valid_for_email(
                    request, account_email
                )
                if request:
                    request.state.invite_pending_consumption_id = invite.id
        else:
            invite = await self._assert_invite_valid_for_email(request, account_email)
            if request:
                request.state.invite_pending_consumption_id = invite.id
                request.state.invite_already_validated = True

        return await super().oauth_callback(  # pyright: ignore[reportAttributeAccessIssue]
            oauth_name,
            access_token,
            account_id,
            account_email,
            expires_at,
            refresh_token,
            request,
            associate_by_email=associate_by_email,
            is_verified_by_default=is_verified_by_default,
        )

    async def create(
        self, user_create, safe: bool = False, request: Optional[Request] = None
    ) -> User:
        already_validated = (
            getattr(request.state, "invite_already_validated", False)
            if request
            else False
        )

        if not already_validated:
            invite = await self._assert_invite_valid_for_email(
                request, user_create.email
            )
            if request:
                request.state.invite_pending_consumption_id = invite.id

        try:
            user = await super().create(user_create, safe=safe, request=request)
        except Exception:
            if request:
                request.state.invite_pending_consumption_id = None
            raise

        pending_id = (
            getattr(request.state, "invite_pending_consumption_id", None)
            if request
            else None
        )
        if request and pending_id:
            await self._consume_invite_by_id(pending_id, user)
            request.state.invite_pending_consumption_id = None

        return user

    def _invite_fail(self, request: Optional[Request], reason: str) -> NoReturn:
        if request:
            request.state.clear_pending_invite_cookie = True
        use_json = bool(
            request and getattr(request.state, "invite_validation_error_as_json", False)
        )
        if use_json:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": reason},
            )
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"{settings.frontend_url}/auth/error?reason={reason}"},
        )

    def _invite_token_from_request(self, request: Optional[Request]) -> str:
        if not request:
            self._invite_fail(request, "no_invite")
        token = getattr(
            request.state, "invite_token_override", None
        ) or request.cookies.get("pending_invite")
        if not token:
            self._invite_fail(request, "no_invite")
        return token

    def _has_invite_token(self, request: Optional[Request]) -> bool:
        if not request:
            return False
        return bool(
            getattr(request.state, "invite_token_override", None)
            or request.cookies.get("pending_invite")
        )

    async def _assert_invite_valid_for_email(
        self, request: Optional[Request], email: str
    ) -> InviteToken:
        token = self._invite_token_from_request(request)
        try:
            return await self.invite_service.validate_invite(token, email)
        except InviteError as e:
            self._invite_fail(request, e.code)

    async def _consume_invite_by_id(self, invite_id: uuid.UUID, user: User) -> None:
        try:
            await self.invite_service.consume_invite(invite_id, user.id)
        except (InviteNotFoundError, InviteExhaustedError, UserNotFoundError):
            pass


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
    invite_service: InviteService = Depends(get_invite_service_for_auth),
    email_sender: SmtpEmailSender = Depends(get_smtp_email_sender),
):
    yield UserManager(
        user_db,
        invite_service,
        RequestPasswordReset(email_sender, settings.frontend_url),
        ResetPassword(),
    )
