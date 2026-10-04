"""Rules that protect an organization's superadmins.

Any superadmin can remove another superadmin directly. Two safeguards apply:
nobody removes their own superadmin access, and an organization always keeps
at least one superadmin.
"""

import uuid

from app.domain.exceptions import (
    CannotRemoveLastSuperadminError,
    CannotRemoveOwnSuperadminError,
)

MINIMUM_SUPERADMINS = 1


def ensure_not_self_removal(
    actor_user_id: uuid.UUID, target_user_id: uuid.UUID
) -> None:
    """A superadmin cannot remove their own superadmin role."""
    if actor_user_id == target_user_id:
        raise CannotRemoveOwnSuperadminError("cannot_remove_own_superadmin")


def ensure_superadmin_remains(current_superadmin_count: int) -> None:
    """Removing one superadmin must leave at least one in the organization."""
    if current_superadmin_count - 1 < MINIMUM_SUPERADMINS:
        raise CannotRemoveLastSuperadminError("cannot_remove_last_superadmin")
