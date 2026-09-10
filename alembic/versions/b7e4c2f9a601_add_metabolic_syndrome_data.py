"""add metabolic syndrome data fields

Revision ID: b7e4c2f9a601
Revises: 91c4d2e7f8a0
Create Date: 2026-09-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e4c2f9a601"
down_revision: Union[str, Sequence[str], None] = "91c4d2e7f8a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MEMBER_HEALTH_FLOAT_COLUMNS = (
    "triglycerides",
    "hdl_cholesterol",
    "systolic_blood_pressure",
    "diastolic_blood_pressure",
    "fasting_glucose",
)
_SUBMISSION_FLOAT_COLUMNS = (
    "diastolic_blood_pressure",
    "hdl_cholesterol",
    "fasting_glucose",
)


def upgrade() -> None:
    for column_name in _MEMBER_HEALTH_FLOAT_COLUMNS:
        op.add_column(
            "member_health_data",
            sa.Column(column_name, sa.Float(), nullable=True),
        )
    op.add_column(
        "member_health_data",
        sa.Column("glucose_lowering_medication", sa.Boolean(), nullable=True),
    )
    for column_name in _SUBMISSION_FLOAT_COLUMNS:
        op.add_column(
            "assessment_submissions",
            sa.Column(column_name, sa.Float(), nullable=True),
        )
    op.add_column(
        "assessment_submissions",
        sa.Column("glucose_lowering_medication", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessment_submissions", "glucose_lowering_medication")
    for column_name in reversed(_SUBMISSION_FLOAT_COLUMNS):
        op.drop_column("assessment_submissions", column_name)
    op.drop_column("member_health_data", "glucose_lowering_medication")
    for column_name in reversed(_MEMBER_HEALTH_FLOAT_COLUMNS):
        op.drop_column("member_health_data", column_name)
