from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_users.db import SQLAlchemyUserDatabase

from app.domain.services.invite import InviteService
from app.infrastructure.email import SmtpEmailSender
from app.infrastructure.authentication.machinery.google_oauth import google_oauth_client
from app.infrastructure.persistence.database import async_session_maker
from app.infrastructure.persistence.models import User, OAuthAccount
from app.infrastructure.persistence.repositories.department import DepartmentRepository
from app.infrastructure.persistence.repositories.invite import InviteRepository
from app.infrastructure.persistence.repositories.membership import MembershipRepository
from app.infrastructure.persistence.repositories.user import UserRepository
from httpx_oauth.clients.google import GoogleOAuth2
from app.infrastructure.time.system_time_provider import SystemTimeProvider


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(
    session: AsyncSession = Depends(get_async_session),
):
    yield SQLAlchemyUserDatabase(
        session,
        User,
        OAuthAccount,
    )


def get_google_oauth_client() -> GoogleOAuth2:
    return google_oauth_client


async def get_invite_service_for_auth(
    session: AsyncSession = Depends(get_async_session),
) -> InviteService:
    return InviteService(
        InviteRepository(session),
        MembershipRepository(session),
        UserRepository(session),
        DepartmentRepository(session),
        time_provider=SystemTimeProvider(),
    )


def get_smtp_email_sender() -> SmtpEmailSender:
    return SmtpEmailSender()
