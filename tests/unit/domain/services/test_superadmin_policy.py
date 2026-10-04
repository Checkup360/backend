import uuid

import pytest

from app.domain.exceptions import (
    CannotRemoveLastSuperadminError,
    CannotRemoveOwnSuperadminError,
)
from app.domain.services.superadmin_policy import (
    ensure_not_self_removal,
    ensure_superadmin_remains,
)


def test_removing_someone_else_is_allowed():
    ensure_not_self_removal(uuid.uuid4(), uuid.uuid4())


def test_removing_yourself_is_rejected():
    user_id = uuid.uuid4()
    with pytest.raises(CannotRemoveOwnSuperadminError):
        ensure_not_self_removal(user_id, user_id)


@pytest.mark.parametrize("count", [2, 3, 10])
def test_removal_allowed_when_another_superadmin_remains(count):
    ensure_superadmin_remains(count)


@pytest.mark.parametrize("count", [0, 1])
def test_removal_rejected_when_no_superadmin_would_remain(count):
    with pytest.raises(CannotRemoveLastSuperadminError):
        ensure_superadmin_remains(count)
