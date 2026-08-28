"""Add content_manager to orgrole enum

Revision ID: 3b7e9d2a1c05
Revises: f84a3c106d0e
Create Date: 2026-08-28 16:23:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3b7e9d2a1c05"
down_revision: Union[str, Sequence[str], None] = "e7381992a101"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'content_manager' value to the orgrole PostgreSQL enum."""
    op.execute("ALTER TYPE orgrole ADD VALUE IF NOT EXISTS 'content_manager'")


def downgrade() -> None:
    """Remove 'content_manager' value from the orgrole PostgreSQL enum.

    PostgreSQL does not support removing enum values directly. The safest
    reversible approach is to recreate the type without the value and migrate
    any rows that use it back to a safe default.

    WARNING: any membership or invite_token row with role='content_manager'
    will be demoted to 'member' on downgrade.
    """
    # Demote content_manager memberships to member before removing the type
    op.execute(
        """
        UPDATE memberships
        SET roles = array_replace(roles, 'content_manager'::orgrole, 'member'::orgrole)
        WHERE 'content_manager'::orgrole = ANY(roles)
        """
    )
    op.execute(
        """
        UPDATE invite_tokens
        SET role = 'member'
        WHERE role = 'content_manager'
        """
    )

    # Recreate the enum without content_manager
    op.execute("ALTER TYPE orgrole RENAME TO orgrole_old")
    op.execute("CREATE TYPE orgrole AS ENUM ('admin', 'member')")

    # Migrate memberships column
    op.execute(
        """
        ALTER TABLE memberships
        ALTER COLUMN roles TYPE orgrole[]
        USING roles::text[]::orgrole[]
        """
    )

    # Migrate invite_tokens column
    op.execute(
        """
        ALTER TABLE invite_tokens
        ALTER COLUMN role TYPE orgrole
        USING role::text::orgrole
        """
    )

    op.execute("DROP TYPE orgrole_old")
