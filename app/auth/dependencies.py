from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_users.db import SQLAlchemyUserDatabase

from app.auth.machinery.google_oauth import google_oauth_client
from app.persistence.database import async_session_maker
from app.persistence.models import User, OAuthAccount
from httpx_oauth.clients.google import GoogleOAuth2


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
