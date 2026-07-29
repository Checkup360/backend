from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.authentication import dependencies


@pytest.mark.asyncio
async def test_get_async_session():
    mock_session = AsyncMock()
    mock_maker = MagicMock()
    mock_maker.return_value.__aenter__.return_value = mock_session

    with patch.object(dependencies, "async_session_maker", mock_maker):
        generator = dependencies.get_async_session()
        session = await anext(generator)
        assert session == mock_session


@pytest.mark.asyncio
async def test_get_user_db():
    session = AsyncMock()
    generator = dependencies.get_user_db(session)
    user_db = await anext(generator)
    assert user_db is not None


def test_get_google_oauth_client():
    client = dependencies.get_google_oauth_client()
    assert client == dependencies.google_oauth_client


@pytest.mark.asyncio
async def test_get_invite_service_for_auth():
    session = AsyncMock()
    invite_service = await dependencies.get_invite_service_for_auth(session)
    assert invite_service is not None


def test_get_smtp_email_sender():
    sender = dependencies.get_smtp_email_sender()
    assert sender is not None


@pytest.mark.asyncio
async def test_get_user_manager():
    from app.infrastructure.authentication.manager import get_user_manager

    user_db = AsyncMock()
    invite_service = AsyncMock()
    email_sender = MagicMock()

    generator = get_user_manager(user_db, invite_service, email_sender)
    manager = await anext(generator)

    assert manager is not None
    assert manager.invite_service == invite_service
