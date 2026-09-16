"""add operational risk fields (nmq, audit-c, pss-10) to member_health_data

Revision ID: e8a2b4c6d819
Revises: d5f1e3a9c782
Create Date: 2026-09-16 00:22:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e8a2b4c6d819"
down_revision: Union[str, Sequence[str], None] = "d5f1e3a9c782"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "member_health_data",
        sa.Column("nordic_nmq_data", sa.JSON(), nullable=True),
    )
    op.add_column(
        "member_health_data",
        sa.Column("audit_c_frequency", sa.Integer(), nullable=True),
    )
    op.add_column(
        "member_health_data",
        sa.Column("audit_c_quantity", sa.Integer(), nullable=True),
    )
    op.add_column(
        "member_health_data",
        sa.Column("audit_c_heavy_drinking", sa.Integer(), nullable=True),
    )
    for i in range(1, 11):
        op.add_column(
            "member_health_data",
            sa.Column(f"pss10_q{i}", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    for i in range(10, 0, -1):
        op.drop_column("member_health_data", f"pss10_q{i}")
    op.drop_column("member_health_data", "audit_c_heavy_drinking")
    op.drop_column("member_health_data", "audit_c_quantity")
    op.drop_column("member_health_data", "audit_c_frequency")
    op.drop_column("member_health_data", "nordic_nmq_data")
