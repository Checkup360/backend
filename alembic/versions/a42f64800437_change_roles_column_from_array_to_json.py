"""Change roles column from ARRAY to JSON

Revision ID: a42f64800437
Revises: a13eba4ff013
Create Date: 2026-05-22 12:20:56.955492

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a42f64800437"
down_revision: Union[str, Sequence[str], None] = "a13eba4ff013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("memberships", sa.Column("roles_json", sa.JSON, nullable=True))

    op.execute("""
        WITH converted_roles AS (
            SELECT user_id, organization_id,
                   jsonb_agg(LOWER(role::text)) as roles_json
            FROM memberships, UNNEST(roles) as role
            GROUP BY user_id, organization_id
        )
        UPDATE memberships m
        SET roles_json = cr.roles_json
        FROM converted_roles cr
        WHERE m.user_id = cr.user_id AND m.organization_id = cr.organization_id
    """)

    op.drop_column("memberships", "roles")

    op.alter_column("memberships", "roles_json", new_column_name="roles")

    op.alter_column("memberships", "roles", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "memberships",
        sa.Column(
            "roles_array",
            sa.ARRAY(sa.Enum("ADMIN", "MEMBER", name="orgrole")),
            nullable=True,
        ),
    )

    op.execute("""
        WITH converted_roles AS (
            SELECT user_id, organization_id,
                   ARRAY(SELECT jsonb_array_elements_text(roles))::orgrole[] as roles_array
            FROM memberships
        )
        UPDATE memberships m
        SET roles_array = cr.roles_array
        FROM converted_roles cr
        WHERE m.user_id = cr.user_id AND m.organization_id = cr.organization_id
    """)

    op.drop_column("memberships", "roles")

    op.alter_column("memberships", "roles_array", new_column_name="roles")

    op.alter_column("memberships", "roles", nullable=False)
