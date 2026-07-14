import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.repositories.user import UserRepository


@pytest.mark.asyncio
async def test_create_user(db: AsyncSession):
    repo = UserRepository(db)
    user = await repo.create(
        email="test@example.com",
        hashed_password="hash",
        is_active=True,
    )
    assert user.id is not None
    assert user.email == "test@example.com"


@pytest.mark.asyncio
async def test_get_user(db: AsyncSession):
    repo = UserRepository(db)
    created = await repo.create(email="findme@example.com", hashed_password="hash")

    found = await repo.get(created.id)
    assert found is not None
    assert found.email == "findme@example.com"


@pytest.mark.asyncio
async def test_update_user_superuser(db: AsyncSession):
    repo = UserRepository(db)
    user = await repo.create(
        email="normal@example.com", hashed_password="hash", is_superuser=False
    )

    updated = await repo.update(user.id, is_superuser=True)
    assert updated.is_superuser is True

    # Check DB
    db_user = await repo.get(user.id)
    assert db_user.is_superuser is True
