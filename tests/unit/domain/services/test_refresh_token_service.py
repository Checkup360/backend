import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from app.domain.entities.refresh_token import RefreshToken
from app.domain.repositories.refresh_token import RefreshTokenRepository
from app.domain.services.refresh_token_service import (
    RefreshTokenService,
    hash_token,
)
from app.domain.services.time_provider import TimeProvider


class FakeTimeProvider(TimeProvider):
    def __init__(self, current_time: datetime):
        self._now = current_time

    def utcnow(self) -> datetime:
        return self._now

    def today(self):
        return self._now.date()

    def advance(self, duration: timedelta):
        self._now += duration


class InMemoryRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self):
        self.tokens: dict[uuid.UUID, RefreshToken] = {}

    async def create_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        token = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
            revoked_at=None,
        )
        self.tokens[token.id] = token
        return token

    async def get_by_token_hash(self, token_hash: str) -> Optional[RefreshToken]:
        for token in self.tokens.values():
            if token.token_hash == token_hash:
                return token
        return None

    async def revoke(self, id: uuid.UUID) -> bool:
        if id in self.tokens and self.tokens[id].revoked_at is None:
            self.tokens[id].revoked_at = datetime.now(timezone.utc)
            return True
        return False

    async def revoke_by_token_hash(self, token_hash: str) -> bool:
        for token in self.tokens.values():
            if token.token_hash == token_hash and token.revoked_at is None:
                token.revoked_at = datetime.now(timezone.utc)
                return True
        return False

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        count = 0
        for token in self.tokens.values():
            if token.user_id == user_id and token.revoked_at is None:
                token.revoked_at = datetime.now(timezone.utc)
                count += 1
        return count


@pytest.fixture
def time_provider():
    return FakeTimeProvider(datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc))


@pytest.fixture
def repo():
    return InMemoryRefreshTokenRepository()


@pytest.fixture
def service(repo, time_provider):
    return RefreshTokenService(
        repository=repo,
        time_provider=time_provider,
        lifetime_seconds=3600,
    )


@pytest.mark.asyncio
async def test_issue_token(service, repo, time_provider):
    user_id = uuid.uuid4()
    raw_token, entity = await service.issue_token(user_id)

    assert raw_token is not None
    assert len(raw_token) > 20
    assert entity.user_id == user_id
    assert entity.token_hash == hash_token(raw_token)
    assert entity.expires_at == time_provider.utcnow() + timedelta(seconds=3600)
    assert entity.is_active is True


@pytest.mark.asyncio
async def test_validate_and_rotate_success(service, repo, time_provider):
    user_id = uuid.uuid4()
    raw_token, old_entity = await service.issue_token(user_id)

    # Rotate token
    ret_user_id, new_raw_token, new_entity = await service.validate_and_rotate(
        raw_token
    )

    assert ret_user_id == user_id
    assert new_raw_token != raw_token
    assert new_entity.user_id == user_id
    assert new_entity.is_active is True

    # Old token must now be revoked
    old_record = await repo.get_by_token_hash(hash_token(raw_token))
    assert old_record.revoked_at is not None
    assert old_record.is_active is False


@pytest.mark.asyncio
async def test_validate_and_rotate_invalid_token(service):
    with pytest.raises(ValueError, match="Invalid refresh token"):
        await service.validate_and_rotate("completely-invalid-token")


@pytest.mark.asyncio
async def test_validate_and_rotate_expired_token(service, time_provider):
    user_id = uuid.uuid4()
    raw_token, _ = await service.issue_token(user_id)

    # Advance time past expiration
    time_provider.advance(timedelta(hours=2))

    with pytest.raises(ValueError, match="expired"):
        await service.validate_and_rotate(raw_token)


@pytest.mark.asyncio
async def test_reuse_detection_revokes_all_user_tokens(service, repo):
    user_id = uuid.uuid4()
    raw_token1, _ = await service.issue_token(user_id)
    raw_token2, _ = await service.issue_token(user_id)

    # Rotate first token normally
    _, new_token, _ = await service.validate_and_rotate(raw_token1)

    # Now attempt to reuse the old raw_token1!
    with pytest.raises(ValueError, match="already revoked"):
        await service.validate_and_rotate(raw_token1)

    # Check that ALL active tokens for this user (including raw_token2 and new_token) are now revoked!
    rec2 = await repo.get_by_token_hash(hash_token(raw_token2))
    assert rec2.revoked_at is not None

    rec_new = await repo.get_by_token_hash(hash_token(new_token))
    assert rec_new.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_token(service, repo):
    user_id = uuid.uuid4()
    raw_token, _ = await service.issue_token(user_id)

    revoked = await service.revoke_token(raw_token)
    assert revoked is True

    record = await repo.get_by_token_hash(hash_token(raw_token))
    assert record.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_all_for_user(service, repo):
    user_id = uuid.uuid4()
    raw1, _ = await service.issue_token(user_id)
    raw2, _ = await service.issue_token(user_id)

    count = await service.revoke_all_for_user(user_id)
    assert count == 2

    rec1 = await repo.get_by_token_hash(hash_token(raw1))
    rec2 = await repo.get_by_token_hash(hash_token(raw2))
    assert rec1.revoked_at is not None
    assert rec2.revoked_at is not None
