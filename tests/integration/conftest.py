import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.infrastructure.persistence.database import Base
from app.presentation.main import app
from app.infrastructure.persistence.models import (
    Department,
    InviteToken,
    Membership,
    Organization,
    User,
)
from app.domain.value_objects.org_role import OrgRole
from testcontainers.postgres import PostgresContainer


DEFAULT_TEST_PASSWORD = "SuperSecure123!"


class AuthScenario:
    def __init__(self, client: TestClient, db_session_maker):
        self.client = client
        self.db_session_maker = db_session_maker

    def login(self, email: str, password: str = DEFAULT_TEST_PASSWORD):
        return self.client.post(
            "/auth/login",
            data={"username": email, "password": password},
            follow_redirects=False,
        )

    async def register_and_login(
        self,
        *,
        email: str,
        password: str = DEFAULT_TEST_PASSWORD,
        is_superuser: bool = False,
        memberships: list[tuple[str, OrgRole]] | None = None,
    ) -> User:
        invite_token = f"invite-{uuid.uuid4()}"
        async with self.db_session_maker() as session:
            session.add(
                InviteToken(
                    token=invite_token,
                    email=email,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    max_uses=1,
                    uses=0,
                )
            )
            await session.commit()

        register_response = self.client.post(
            f"/invites/{invite_token}/redeem",
            json={"email": email, "password": password},
            follow_redirects=False,
        )
        assert register_response.status_code == 303

        async with self.db_session_maker() as session:
            user = await session.scalar(select(User).where(User.email == email))
            assert user is not None
            user.is_superuser = is_superuser

            if memberships:
                for slug, role in memberships:
                    organization = Organization(
                        name=slug.replace("-", " ").title(), slug=slug
                    )
                    session.add(organization)
                    await session.flush()
                    session.add(
                        Membership(
                            user_id=user.id,
                            organization_id=organization.id,
                            roles=[role],
                        )
                    )

            await session.commit()
            await session.refresh(user)
            user_id = user.id

        self.client.cookies.clear()
        login_response = self.login(email=email, password=password)
        assert login_response.status_code == 303

        async with self.db_session_maker() as session:
            fresh_user = await session.get(User, user_id)
            assert fresh_user is not None
            return fresh_user


@pytest.fixture(scope="session")
def postgres_container():
    postgres = PostgresContainer("postgres:16-alpine", driver="asyncpg")
    postgres.with_command(
        "postgres -c fsync=off -c synchronous_commit=off -c full_page_writes=off"
    )
    with postgres:
        yield postgres


@pytest_asyncio.fixture(scope="session")
async def pg_engine(postgres_container):
    """Engine compartido por todos los tests. El schema se crea una sola vez."""
    database_url = postgres_container.get_connection_url()

    engine = create_async_engine(database_url, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session_maker(pg_engine, monkeypatch):
    session_maker = async_sessionmaker(
        bind=pg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    from app.infrastructure.authentication import dependencies as auth_dependencies
    from app.infrastructure.authentication.middleware import (
        db_session as auth_middleware,
    )
    import app.infrastructure.persistence.database as database_module

    monkeypatch.setattr(database_module, "async_session_maker", session_maker)
    monkeypatch.setattr(auth_dependencies, "async_session_maker", session_maker)
    monkeypatch.setattr(auth_middleware, "async_session_maker", session_maker)

    yield session_maker

    table_names = ", ".join(
        f'"{t.schema}".' if t.schema else "" + f'"{t.name}"'
        for t in Base.metadata.sorted_tables
    )
    async with pg_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def client(db_session_maker):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_scenario(client, db_session_maker):
    return AuthScenario(client=client, db_session_maker=db_session_maker)


@pytest_asyncio.fixture()
async def make_user(db_session_maker):
    async def _make_user(*, email: str = None, is_superuser: bool = False) -> User:
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
        department_id=None,
    ) -> Membership:
        membership = Membership(
            user_id=user_id,
            organization_id=organization_id,
            roles=[OrgRole(role)],
            department_id=department_id,
        )
        async with db_session_maker() as session:
            session.add(membership)
            await session.commit()
            await session.refresh(membership)
        return membership

    return _make_membership


@pytest_asyncio.fixture()
async def make_department(db_session_maker):
    async def _make_department(
        *,
        organization_id,
        name: str = "People",
        slug: str = "people",
    ) -> Department:
        department = Department(
            organization_id=organization_id,
            name=name,
            slug=slug,
        )
        async with db_session_maker() as session:
            session.add(department)
            await session.commit()
            await session.refresh(department)
        return department

    return _make_department


@pytest_asyncio.fixture()
async def make_invite(db_session_maker):
    async def _make_invite(
        *,
        token: str | None = None,
        email: str | None = "test@example.com",
        expires_in_hours: int = 1,
        max_uses: int = 1,
        uses: int = 0,
        organization_id=None,
        role: OrgRole | None = None,
        is_sysadmin: bool = False,
    ) -> InviteToken:
        invite = InviteToken(
            token=token or f"invite-{uuid.uuid4()}",
            email=email,
            max_uses=max_uses,
            uses=uses,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
            organization_id=organization_id,
            role=role,
            is_sysadmin=is_sysadmin,
        )
        async with db_session_maker() as session:
            session.add(invite)
            await session.commit()
            await session.refresh(invite)
            return invite

    return _make_invite


@pytest_asyncio.fixture()
async def db(db_session_maker):
    """Fixture para obtener una sesión de BD en un contexto async."""
    async with db_session_maker() as session:
        yield session
