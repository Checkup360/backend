import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.auth.users import current_active_user
from app.database import Base
from app.main import app
from app.models import Organization, User, Membership
from app.models.membership import OrgRole


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


@pytest.fixture()
def override_current_user():
    def _override(user):
        app.dependency_overrides[current_active_user] = lambda: user

    yield _override
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def make_user(db_session_maker):
    async def _make_user(*, email: str = None, is_superuser: bool = False) -> User:
        import uuid

        user = User(
            id=uuid.uuid4(),
            email=email or f"{uuid.uuid4()}@example.com",
            hashed_password="not-used",
            is_active=True,
            is_superuser=is_superuser,
            is_verified=False,
        )
        async with db_session_maker() as session:
            session.add(user)
            await session.commit()
        return user

    return _make_user


@pytest_asyncio.fixture()
async def make_organization(db_session_maker):
    async def _make_organization(
        *, name: str = "Test Org", slug: str = "test-org"
    ) -> Organization:
        organization = Organization(name=name, slug=slug)
        async with db_session_maker() as session:
            session.add(organization)
            await session.commit()
            await session.refresh(organization)
        return organization

    return _make_organization


@pytest_asyncio.fixture()
async def make_membership(db_session_maker):
    async def _make_membership(
        *,
        user_id,
        organization_id,
        role: str = "member",
    ) -> Membership:
        membership = Membership(
            user_id=user_id,
            organization_id=organization_id,
            role=OrgRole(role),
        )
        async with db_session_maker() as session:
            session.add(membership)
            await session.commit()
            await session.refresh(membership)
        return membership

    return _make_membership
