"""Fix orgrole enum: rename content_manager to CONTENT_MANAGER

Revision ID: 9c4f1e8b2d07
Revises: 3b7e9d2a1c05
Create Date: 2026-08-28 16:39:00.000000

The original orgrole enum was created with uppercase values ('ADMIN', 'MEMBER')
because SQLAlchemy serializes Python enum members by *name* (not value) when no
values_callable is set. The previous migration incorrectly added 'content_manager'
(lowercase), which caused write failures. This migration recreates the type with
the correct uppercase 'CONTENT_MANAGER' value, consistent with the rest.

No data loss occurs: no rows with 'content_manager' could have been inserted
because the application was raising a 500 on every attempt.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9c4f1e8b2d07"
down_revision: Union[str, Sequence[str], None] = "3b7e9d2a1c05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Recreate orgrole enum replacing lowercase 'content_manager' with 'CONTENT_MANAGER'."""
    # Convert enum columns to plain text so we can drop and recreate the type.
    op.execute("ALTER TABLE invite_tokens ALTER COLUMN role TYPE text USING role::text")
    op.execute(
        "ALTER TABLE memberships ALTER COLUMN roles TYPE text[] USING roles::text[]"
    )

    op.execute("DROP TYPE orgrole")
    op.execute("CREATE TYPE orgrole AS ENUM ('ADMIN', 'MEMBER', 'CONTENT_MANAGER')")

    # Restore columns — any stray lowercase 'content_manager' values are coerced.
    op.execute(
        """
        UPDATE invite_tokens
        SET role = 'CONTENT_MANAGER'
        WHERE role = 'content_manager'
        """
    )
    op.execute(
        """
        UPDATE memberships
        SET roles = array_replace(roles, 'content_manager', 'CONTENT_MANAGER')
        WHERE 'content_manager' = ANY(roles)
        """
    )

    op.execute(
        "ALTER TABLE invite_tokens ALTER COLUMN role TYPE orgrole USING role::orgrole"
    )
    op.execute(
        "ALTER TABLE memberships ALTER COLUMN roles TYPE orgrole[] USING roles::orgrole[]"
    )


def downgrade() -> None:
    """Revert CONTENT_MANAGER to content_manager (lowercase)."""
    op.execute("ALTER TABLE invite_tokens ALTER COLUMN role TYPE text USING role::text")
    op.execute(
        "ALTER TABLE memberships ALTER COLUMN roles TYPE text[] USING roles::text[]"
    )

    op.execute("DROP TYPE orgrole")
    op.execute("CREATE TYPE orgrole AS ENUM ('ADMIN', 'MEMBER', 'content_manager')")

    op.execute(
        """
        UPDATE invite_tokens
        SET role = 'content_manager'
        WHERE role = 'CONTENT_MANAGER'
        """
    )
    op.execute(
        """
        UPDATE memberships
        SET roles = array_replace(roles, 'CONTENT_MANAGER', 'content_manager')
        WHERE 'CONTENT_MANAGER' = ANY(roles)
        """
    )

    op.execute(
        "ALTER TABLE invite_tokens ALTER COLUMN role TYPE orgrole USING role::orgrole"
    )
    op.execute(
        "ALTER TABLE memberships ALTER COLUMN roles TYPE orgrole[] USING roles::orgrole[]"
    )
