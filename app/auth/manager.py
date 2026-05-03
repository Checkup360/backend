import uuid
from datetime import datetime, timezone
from typing import NoReturn, Optional

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_user_db
from app.core import settings
from app.invites.cookies import clear_pending_invite_cookie
from app.models import User
from app.models.invite import InviteToken
from app.schemas.invite import InviteRejected


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.auth_secret
    verification_token_secret = settings.auth_secret

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ) -> None:
        pass

    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
        response: Optional[Response] = None,
    ) -> None:
        if not request or not response:
            return
        if request.cookies.get("pending_invite"):
            clear_pending_invite_cookie(response)

    async def oauth_callback(
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
        """
        Usuario existente: sin invite.
        Usuario nuevo: valida invite (sin consumir); el consumo ocurre al crear el usuario en create().
        """
        existing_user = await self.user_db.get_by_oauth_account(oauth_name, account_id)

        if existing_user:
            return await super().oauth_callback(
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

        invite = await self._assert_invite_valid_for_email(request, account_email)
        if request:
            request.state.invite_pending_consumption_id = invite.id
            request.state.invite_already_validated = True

        return await super().oauth_callback(
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
            await self._consume_invite_by_id(request, pending_id, user.email)
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
                detail=InviteRejected(code=reason).model_dump(),
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

    async def _assert_invite_valid_for_email(
        self, request: Optional[Request], email: str
    ) -> InviteToken:
        """Comprueba el invite; no lo marca como usado."""
        token = self._invite_token_from_request(request)
        assert request is not None
        db: AsyncSession = request.state.db
        invite = await db.scalar(select(InviteToken).where(InviteToken.token == token))

        if not invite:
            self._invite_fail(request, "invalid_invite")

        if invite.used:
            self._invite_fail(request, "invite_used")

        expires_at = invite.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            self._invite_fail(request, "invite_expired")

        if invite.email and invite.email != email:
            self._invite_fail(request, "email_mismatch")

        return invite

    async def _consume_invite_by_id(
        self, request: Request, invite_id: uuid.UUID, used_by_email: str
    ) -> None:
        """Marca el invite como usado solo después de que el usuario se creó bien."""
        db: AsyncSession = request.state.db
        invite = await db.get(InviteToken, invite_id)
        if invite is None or invite.used:
            return
        invite.used = True
        invite.used_by = used_by_email
        await db.commit()


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
):
    yield UserManager(user_db)
