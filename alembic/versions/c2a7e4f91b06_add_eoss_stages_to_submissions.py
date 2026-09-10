"""add EOSS stages to assessment submissions

Revision ID: c2a7e4f91b06
Revises: b7e4c2f9a601
Create Date: 2026-09-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2a7e4f91b06"
down_revision: Union[str, Sequence[str], None] = "b7e4c2f9a601"
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
            "assessment_submissions",
            sa.Column(column_name, sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    for column_name in reversed(_COLUMNS):
        op.drop_column("assessment_submissions", column_name)
