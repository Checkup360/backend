import uuid
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.entities.org_role import OrgRole
from app.domain.services.member_details import MemberDetailsService


def make_user(*, is_superuser=False, roles=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        is_superuser=is_superuser,
        memberships=[
            SimpleNamespace(roles=[role])
            for role in (roles if roles is not None else [OrgRole.MEMBER])
        ],
    )


@pytest.mark.asyncio
async def test_requires_onboarding_for_member_user_without_details():
    repo = AsyncMock()
    repo.exists_for_user.return_value = False

    users = [
        make_user(roles=[OrgRole.MEMBER]),
        make_user(roles=[OrgRole.MEMBER, OrgRole.ADMIN]),
    ]

    service = MemberDetailsService(repo)

    for user in users:
        assert await service.requires_onboarding(user) is True
        repo.exists_for_user.assert_awaited_with(user.id)


@pytest.mark.asyncio
async def test_does_not_require_onboarding_for_member_with_details():
    repo = AsyncMock()
    repo.exists_for_user.return_value = True
    user = make_user(roles=[OrgRole.MEMBER])

    service = MemberDetailsService(repo)

    assert await service.requires_onboarding(user) is False


@pytest.mark.asyncio
async def test_does_not_require_onboarding_for_sysadmin_or_non_member():
    repo = AsyncMock()
    service = MemberDetailsService(repo)

    users = [
        make_user(is_superuser=True, roles=[OrgRole.MEMBER]),
        make_user(roles=[OrgRole.ADMIN]),
        make_user(roles=[]),
    ]

    for user in users:
        assert await service.requires_onboarding(user) is False

    repo.exists_for_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_onboarding_rejects_future_date():
    repo = AsyncMock()
    service = MemberDetailsService(repo)

    with pytest.raises(ValueError, match="date_of_birth_in_future"):
        await service.complete_onboarding(make_user(), date.today() + timedelta(days=1))

    repo.save.assert_not_awaited()
