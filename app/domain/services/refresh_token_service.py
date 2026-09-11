import hashlib
import secrets
import uuid
from datetime import timedelta

from app.domain.entities.refresh_token import RefreshToken
from app.domain.repositories.refresh_token import RefreshTokenRepository
from app.domain.services.time_provider import TimeProvider


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_raw_token() -> str:
    return secrets.token_urlsafe(64)


class RefreshTokenService:
    def __init__(
        self,
        repository: RefreshTokenRepository,
        time_provider: TimeProvider,
        lifetime_seconds: int = 2592000,
    ):
        self.repository = repository
        self.time_provider = time_provider
        self.lifetime_seconds = lifetime_seconds

    async def issue_token(self, user_id: uuid.UUID) -> tuple[str, RefreshToken]:
        raw_token = generate_raw_token()
        token_hash = hash_token(raw_token)
        now = self.time_provider.utcnow()
        expires_at = now + timedelta(seconds=self.lifetime_seconds)
        entity = await self.repository.create_token(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        return raw_token, entity

    async def validate_and_rotate(
        self, raw_token: str
    ) -> tuple[uuid.UUID, str, RefreshToken]:
        token_hash = hash_token(raw_token)
        token_record = await self.repository.get_by_token_hash(token_hash)
        if token_record is None:
            raise ValueError("Invalid refresh token")

        if token_record.revoked_at is not None:
            # Token reuse detected! Revoke all tokens for this user for security
            await self.repository.revoke_all_for_user(token_record.user_id)
            raise ValueError("Refresh token was already revoked (possible token reuse)")

        now = self.time_provider.utcnow()
        if token_record.expires_at <= now:
            raise ValueError("Refresh token has expired")

        # Revoke old token
        await self.repository.revoke(token_record.id)

        # Issue new rotated token
        new_raw_token, new_entity = await self.issue_token(token_record.user_id)
        return token_record.user_id, new_raw_token, new_entity

    async def revoke_token(self, raw_token: str) -> bool:
        token_hash = hash_token(raw_token)
        return await self.repository.revoke_by_token_hash(token_hash)

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        return await self.repository.revoke_all_for_user(user_id)
