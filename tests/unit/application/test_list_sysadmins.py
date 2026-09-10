import uuid
from unittest.mock import AsyncMock

import pytest

from app.application.use_cases.admin.list_sysadmins import ListSysadminsUseCase
from app.domain.entities import MemberDetails, User


@pytest.mark.asyncio
async def test_list_sysadmins_use_case():
    mock_user_repo = AsyncMock()
    mock_invite_repo = AsyncMock()

    user1 = User(
        id=uuid.uuid4(), email="sysadmin1@test.com", is_superuser=True, is_active=True
    )
    details1 = MemberDetails(
        user_id=user1.id,
        date_of_birth="1990-01-01",  # type: ignore
        first_name="Alice",
        last_name="Admin",
    )
    user2 = User(
        id=uuid.uuid4(), email="sysadmin2@test.com", is_superuser=True, is_active=False
    )

    mock_user_repo.list_sysadmins.return_value = ([(user1, details1), (user2, None)], 2)
    mock_user_repo.count_sysadmins.side_effect = [2, 1]  # total=2, active=1
    mock_invite_repo.list_filtered.return_value = ([], 3)  # 3 pending invites

    use_case = ListSysadminsUseCase(mock_user_repo, mock_invite_repo)

    items, total = await use_case.list_sysadmins(
        search="admin", is_active=True, page=1, page_size=10
    )
    assert total == 2
    assert len(items) == 2
    assert items[0].user.email == "sysadmin1@test.com"
    assert items[0].details.first_name == "Alice"
    assert items[1].user.email == "sysadmin2@test.com"
    assert items[1].details is None

    stats = await use_case.get_stats()
    assert stats.total_sysadmins == 2
    assert stats.active_sysadmins == 1
    assert stats.pending_invites == 3
