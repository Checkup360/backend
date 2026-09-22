"""add_superadmin_role_and_invite_flag

Revision ID: a0a6c5969b76
Revises: f1a8b9c0d2e3
Create Date: 2026-09-22 16:09:52.719161

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a0a6c5969b76"
down_revision: Union[str, Sequence[str], None] = "f1a8b9c0d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'superadmin' value to orgrole enum and add is_superadmin to invite_tokens."""
    op.execute("ALTER TYPE orgrole ADD VALUE IF NOT EXISTS 'superadmin'")
    op.add_column(
        "invite_tokens",
        sa.Column(
            "is_superadmin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Remove 'superadmin' from orgrole enum and drop is_superadmin from invite_tokens."""
    op.drop_column("invite_tokens", "is_superadmin")

    # Demote superadmin memberships to admin before removing the enum value
    op.execute(
        """
        UPDATE memberships
        SET roles = array_replace(roles, 'superadmin'::orgrole, 'admin'::orgrole)
        WHERE 'superadmin'::orgrole = ANY(roles)
        """
    )
    op.execute(
        """
        UPDATE invite_tokens
        SET role = 'admin'
        WHERE role = 'superadmin'
        """
    )

    # Recreate the enum without superadmin
    op.execute("ALTER TYPE orgrole RENAME TO orgrole_old")
    op.execute("CREATE TYPE orgrole AS ENUM ('admin', 'member', 'content_manager')")

    op.execute(
        """
        ALTER TABLE memberships
        ALTER COLUMN roles TYPE orgrole[]
        USING roles::text[]::orgrole[]
        """
    )
    op.execute(
        """
        ALTER TABLE invite_tokens
        ALTER COLUMN role TYPE orgrole
        USING role::text::orgrole
        """
    )

    op.execute("DROP TYPE orgrole_old")
