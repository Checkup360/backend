import uuid
from datetime import datetime
from typing import Protocol

from app.domain.entities.refresh_token import RefreshToken


class RefreshTokenRepository(Protocol):
    async def create_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken: ...

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None: ...

    async def revoke(self, id: uuid.UUID) -> bool: ...

    async def revoke_by_token_hash(self, token_hash: str) -> bool: ...

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int: ...
