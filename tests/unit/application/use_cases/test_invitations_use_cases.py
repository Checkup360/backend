import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.use_cases.invitations import (
    DeleteInvites,
    InviteUrlBuilder,
    ListInvites,
)
from app.domain.value_objects import OrgRole


# --- DeleteInvites Tests ---


@pytest.mark.asyncio
async def test_delete_invites_delegates_to_repository_delete_filtered():
    repo = AsyncMock()
    repo.delete_filtered.return_value = 2
    org_id = uuid.uuid4()
    invite_ids = [uuid.uuid4(), uuid.uuid4()]

    use_case = DeleteInvites(repo)
    result = await use_case.execute(
        ids=invite_ids,
        is_sysadmin=False,
        organization_id=org_id,
    )

    assert result == 2
    repo.delete_filtered.assert_awaited_once_with(
        ids=invite_ids,
        is_sysadmin=False,
        organization_id=org_id,
    )


@pytest.mark.asyncio
async def test_delete_invites_as_sysadmin():
    repo = AsyncMock()
    repo.delete_filtered.return_value = 5
    invite_ids = [uuid.uuid4()]

    use_case = DeleteInvites(repo)
    result = await use_case.execute(
        ids=invite_ids,
        is_sysadmin=True,
        organization_id=None,
    )

    assert result == 5
    repo.delete_filtered.assert_awaited_once_with(
        ids=invite_ids,
        is_sysadmin=True,
        organization_id=None,
    )


@pytest.mark.asyncio
async def test_delete_invites_empty_ids():
    repo = AsyncMock()
    repo.delete_filtered.return_value = 0

    use_case = DeleteInvites(repo)
    result = await use_case.execute(
        ids=[],
        is_sysadmin=False,
        organization_id=uuid.uuid4(),
    )

    assert result == 0
    repo.delete_filtered.assert_awaited_once()


# --- InviteUrlBuilder Tests ---


def test_invite_url_builder_strips_trailing_slash_and_formats_url():
    builder = InviteUrlBuilder("https://app.example.com/")
    url = builder.build("abc-123")
    assert url == "https://app.example.com/invite/abc-123"


def test_invite_url_builder_encodes_special_characters_in_token():
    builder = InviteUrlBuilder("https://app.example.com")
    url = builder.build("token/with special?chars#")
    assert url == "https://app.example.com/invite/token%2Fwith%20special%3Fchars%23"


# --- ListInvites Tests ---


@pytest.mark.asyncio
async def test_list_invites_parses_valid_role_and_normalizes_status():
    repo = AsyncMock()
    mock_invites = [MagicMock(), MagicMock()]
    repo.list_filtered.return_value = (mock_invites, 2)
    org_id = uuid.uuid4()

    use_case = ListInvites(repo)
    invites, count = await use_case.execute(
        organization_id=org_id,
        is_sysadmin=False,
        role="ADMIN",
        status="PENDING",
        page=1,
        page_size=10,
    )

    assert invites == mock_invites
    assert count == 2
    repo.list_filtered.assert_awaited_once_with(
        organization_id=org_id,
        is_sysadmin=False,
        role=OrgRole.ADMIN,
        status="pending",
        page=1,
        page_size=10,
    )


@pytest.mark.asyncio
async def test_list_invites_handles_invalid_role_gracefully():
    repo = AsyncMock()
    repo.list_filtered.return_value = ([], 0)
    org_id = uuid.uuid4()

    use_case = ListInvites(repo)
    invites, count = await use_case.execute(
        organization_id=org_id,
        is_sysadmin=False,
        role="NON_EXISTENT_ROLE",
        status="ACTIVE",
        page=1,
        page_size=20,
    )

    assert invites == []
    assert count == 0
    repo.list_filtered.assert_awaited_once_with(
        organization_id=org_id,
        is_sysadmin=False,
        role=None,
        status="active",
        page=1,
        page_size=20,
    )


@pytest.mark.asyncio
async def test_list_invites_handles_none_role_and_status():
    repo = AsyncMock()
    repo.list_filtered.return_value = ([], 0)

    use_case = ListInvites(repo)
    await use_case.execute(
        organization_id=None,
        is_sysadmin=True,
        role=None,
        status=None,
        page=None,
        page_size=50,
    )

    repo.list_filtered.assert_awaited_once_with(
        organization_id=None,
        is_sysadmin=True,
        role=None,
        status=None,
        page=None,
        page_size=50,
    )
