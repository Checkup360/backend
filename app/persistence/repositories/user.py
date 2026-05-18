from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import get_db
from app.domain.entities import User
from app.persistence.models.user import User as UserORM
from app.persistence.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserORM, User]):
    def __init__(self, db: AsyncSession):
        super().__init__(UserORM, db)

    @staticmethod
    def _to_domain(orm: UserORM) -> User:
        return User(
            id=orm.id,
            email=orm.email,
            is_superuser=orm.is_superuser,
            is_active=orm.is_active,
        )


async def get_user_repository(db: AsyncSession = Depends(get_db)):
    return UserRepository(db)
