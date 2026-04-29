import uuid
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_user_db
from app.core import settings
from app.models import User, InviteToken


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.auth_secret
    verification_token_secret = settings.auth_secret

    async def on_after_register(
        self, user: User, request: Optional[Request] = None
    ) -> None:
        print(f"User {user.id} has registered.")

    async def oauth_callback(
        self,
        oauth_name: str,
        access_token: str,
        account_id: str,
        account_email: str,
        account_data: dict,
        request: Optional[Request] = None,
        *args,
        **kwargs,
    ) -> User:
        """
        Override de oauth_callback para validar invite en nuevos usuarios.
        Si el usuario ya existe (login), deja pasar.
        Si es nuevo (registro), valida que tenga un invite válido.
        """
        # Primero, chequear si el usuario YA existe (por OAuth account)
        existing_user = await self.user_db.get_by_oauth_account(oauth_name, account_id)

        if existing_user:
            # Usuario ya registrado → dejalo pasar sin invite
            pos_args = (oauth_name, access_token, account_id, account_email, account_data, request) + args
            return await super().oauth_callback(*pos_args, **kwargs)

        # Usuario nuevo → necesita invite válido
        await self._validate_and_consume_invite(request, account_email)

        # Marcar que ya validamos para que create() no lo haga de nuevo
        if request:
            request.state.invite_already_validated = True

        pos_args = (oauth_name, access_token, account_id, account_email, account_data, request) + args
        return await super().oauth_callback(*pos_args, **kwargs)

    async def create(
        self, user_create, safe: bool = False, request: Optional[Request] = None
    ) -> User:
        """
        Override de create para validar invite en registro con email/password.
        Salta validación si oauth_callback ya la hizo.
        """
        already_validated = (
            getattr(request.state, "invite_already_validated", False) if request else False
        )

        if not already_validated:
            await self._validate_and_consume_invite(request, user_create.email)

        return await super().create(user_create, safe=safe, request=request)

    async def _validate_and_consume_invite(
        self, request: Optional[Request], email: str
    ) -> None:
        """
        Valida y consume un invite token. Levanta HTTPException si falla.
        Lee el token de:
        1. request.state.invite_token_override (para registro email/password)
        2. request.cookies.get("pending_invite") (para OAuth)
        """
        # request may be None in some fastapi-users callbacks; treat that as "no invite provided"
        invite_token = None
        if request:
            invite_token = (
                getattr(request.state, "invite_token_override", None)
                or request.cookies.get("pending_invite")
            )

        if not invite_token:
            # No token available (either no cookie or no override)
            raise HTTPException(
                status_code=303,
                headers={"Location": f"{settings.frontend_url}/auth/error?reason=no_invite"},
            )

        db: AsyncSession = request.state.db
        invite = await db.scalar(
            select(InviteToken).where(InviteToken.token == invite_token)
        )

        if not invite:
            raise HTTPException(
                status_code=303,
                headers={
                    "Location": f"{settings.frontend_url}/auth/error?reason=invalid_invite"
                },
            )

        if invite.used:
            raise HTTPException(
                status_code=303,
                headers={"Location": f"{settings.frontend_url}/auth/error?reason=invite_used"},
            )

        if invite.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=303,
                headers={
                    "Location": f"{settings.frontend_url}/auth/error?reason=invite_expired"
                },
            )

        if invite.email and invite.email != email:
            raise HTTPException(
                status_code=303,
                headers={
                    "Location": f"{settings.frontend_url}/auth/error?reason=email_mismatch"
                },
            )

        # Consumir invite
        invite.used = True
        invite.used_by = email
        await db.commit()


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
):
    yield UserManager(user_db)

