"""add EOSS self-assessment stages to member health data

Revision ID: d4f8a2c6e109
Revises: c2a7e4f91b06
Create Date: 2026-09-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f8a2c6e109"
down_revision: Union[str, Sequence[str], None] = "c2a7e4f91b06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = (
    "eoss_physical_health_stage",
    "eoss_mental_health_stage",
    "eoss_functional_stage",
)


def upgrade() -> None:
    for column_name in _COLUMNS:
        op.add_column(
            "member_health_data",
            sa.Column(column_name, sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    for column_name in reversed(_COLUMNS):
        op.drop_column("member_health_data", column_name)
