"""fix_orgrole_superadmin_case

Revision ID: cc873d9740ce
Revises: b2c3d4e5f6a7
Create Date: 2026-09-22 18:02:14.953027

The orgrole enum in PostgreSQL uses uppercase values ('ADMIN', 'MEMBER', 'CONTENT_MANAGER')
because SQLAlchemy serializes Python enum members by member name when no values_callable
is set. Migration a0a6c5969b76 added lowercase 'superadmin' instead of 'SUPERADMIN',
causing SQLAlchemy inserts and updates with OrgRole.SUPERADMIN to fail with:
    ERROR: invalid input value for enum orgrole: "SUPERADMIN"

This migration recreates the orgrole enum with canonical uppercase 'SUPERADMIN'.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "cc873d9740ce"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Recreate orgrole enum with uppercase 'SUPERADMIN' and migrate any stray lowercase values."""
    op.execute("ALTER TABLE invite_tokens ALTER COLUMN role TYPE text USING role::text")
    op.execute(
        "ALTER TABLE memberships ALTER COLUMN roles TYPE text[] USING roles::text[]"
    )

    op.execute("DROP TYPE orgrole")
    op.execute(
        "CREATE TYPE orgrole AS ENUM ('ADMIN', 'MEMBER', 'CONTENT_MANAGER', 'SUPERADMIN')"
    )

    op.execute(
        """
        UPDATE invite_tokens
        SET role = 'SUPERADMIN'
        WHERE role = 'superadmin'
        """
    )
    op.execute(
        """
        UPDATE memberships
        SET roles = array_replace(roles, 'superadmin', 'SUPERADMIN')
        WHERE 'superadmin' = ANY(roles)
        """
    )

    op.execute(
        "ALTER TABLE invite_tokens ALTER COLUMN role TYPE orgrole USING role::orgrole"
    )
    op.execute(
        "ALTER TABLE memberships ALTER COLUMN roles TYPE orgrole[] USING roles::orgrole[]"
    )


def downgrade() -> None:
    """Revert orgrole enum removing SUPERADMIN."""
    op.execute("ALTER TABLE invite_tokens ALTER COLUMN role TYPE text USING role::text")
    op.execute(
        "ALTER TABLE memberships ALTER COLUMN roles TYPE text[] USING roles::text[]"
    )

    op.execute(
        """
        UPDATE invite_tokens
        SET role = 'ADMIN'
        WHERE role = 'SUPERADMIN'
        """
    )
    op.execute(
        """
        UPDATE memberships
        SET roles = array_replace(roles, 'SUPERADMIN', 'ADMIN')
        WHERE 'SUPERADMIN' = ANY(roles)
        """
    )

    op.execute("DROP TYPE orgrole")
    op.execute(
        "CREATE TYPE orgrole AS ENUM ('ADMIN', 'MEMBER', 'CONTENT_MANAGER', 'superadmin')"
    )

    op.execute(
        "ALTER TABLE invite_tokens ALTER COLUMN role TYPE orgrole USING role::orgrole"
    )
    op.execute(
        "ALTER TABLE memberships ALTER COLUMN roles TYPE orgrole[] USING roles::orgrole[]"
    )
