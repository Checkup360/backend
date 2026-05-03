import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app


@pytest_asyncio.fixture()
async def db_session_maker(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    from app.auth import dependencies as auth_dependencies
    from app.auth import middleware as auth_middleware
    import app.database as database_module

    monkeypatch.setattr(database_module, "engine", engine)
    monkeypatch.setattr(database_module, "async_session_maker", session_maker)
    monkeypatch.setattr(auth_dependencies, "async_session_maker", session_maker)
    monkeypatch.setattr(auth_middleware, "async_session_maker", session_maker)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield session_maker
    finally:
        await engine.dispose()


@pytest.fixture()
def client(db_session_maker):
    with TestClient(app) as test_client:
        yield test_client
