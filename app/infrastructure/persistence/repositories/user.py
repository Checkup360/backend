from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import User
from app.infrastructure.persistence.models.user import User as UserORM
from app.infrastructure.persistence.repositories.base import BaseRepository


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

    def _from_domain(self, entity: User) -> dict:
        return {
            "id": entity.id,
            "email": entity.email,
            "is_superuser": entity.is_superuser,
            "is_active": entity.is_active,
        }
