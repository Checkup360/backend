"""add phq9 mood columns to health data and submissions

Revision ID: 8f3c1a7e2b14
Revises: 4d2e8f1a9b03
Create Date: 2026-09-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f3c1a7e2b14"
down_revision: Union[str, Sequence[str], None] = "4d2e8f1a9b03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PHQ9_COLUMNS = (
    "little_interest",
    "feeling_down",
    "sleep_trouble",
    "tired_energy",
    "appetite",
    "feeling_bad",
    "concentration",
    "psychomotor",
    "self_harm_thoughts",
)


def upgrade() -> None:
    for column_name in _PHQ9_COLUMNS:
        op.add_column(
            "member_health_data",
            sa.Column(column_name, sa.Integer(), nullable=True),
        )
        op.add_column(
            "assessment_submissions",
            sa.Column(column_name, sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    for column_name in reversed(_PHQ9_COLUMNS):
        op.drop_column("assessment_submissions", column_name)
        op.drop_column("member_health_data", column_name)
