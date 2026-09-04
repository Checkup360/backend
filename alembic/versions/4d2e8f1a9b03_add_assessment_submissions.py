"""add assessment submissions

Revision ID: 4d2e8f1a9b03
Revises: 07bf91de8dc4
Create Date: 2026-09-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4d2e8f1a9b03"
down_revision: Union[str, Sequence[str], None] = "07bf91de8dc4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assessment_submissions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("form_type", sa.String(length=100), nullable=False),
        sa.Column("form_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("sex", sa.String(length=30), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("waist_circumference", sa.Float(), nullable=True),
        sa.Column("systolic_blood_pressure", sa.Float(), nullable=True),
        sa.Column("total_cholesterol", sa.Float(), nullable=True),
        sa.Column("hdl", sa.Float(), nullable=True),
        sa.Column("triglycerides", sa.Float(), nullable=True),
        sa.Column("smoker", sa.Boolean(), nullable=True),
        sa.Column("daily_physical_activity", sa.Boolean(), nullable=True),
        sa.Column("fruits_vegetables", sa.Boolean(), nullable=True),
        sa.Column("hypertension_medication", sa.Boolean(), nullable=True),
        sa.Column("previous_high_glucose", sa.Boolean(), nullable=True),
        sa.Column("family_diabetes", sa.String(length=30), nullable=True),
        sa.Column("snoring", sa.Boolean(), nullable=True),
        sa.Column("tired", sa.Boolean(), nullable=True),
        sa.Column("observed_apnea", sa.Boolean(), nullable=True),
        sa.Column("neck_circumference", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assessment_submissions_user_submitted_at",
        "assessment_submissions",
        ["user_id", "submitted_at"],
    )
    op.create_index(
        "ix_assessment_submissions_org_submitted_at",
        "assessment_submissions",
        ["organization_id", "submitted_at"],
    )
    op.create_index(
        op.f("ix_assessment_submissions_status"),
        "assessment_submissions",
        ["status"],
    )
    op.add_column(
        "risk_scores",
        sa.Column("submission_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_risk_scores_submission_id",
        "risk_scores",
        "assessment_submissions",
        ["submission_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_risk_scores_submission_id"),
        "risk_scores",
        ["submission_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_risk_scores_submission_id"), table_name="risk_scores")
    op.drop_constraint(
        "fk_risk_scores_submission_id", "risk_scores", type_="foreignkey"
    )
    op.drop_column("risk_scores", "submission_id")
    op.drop_index(
        op.f("ix_assessment_submissions_status"),
        table_name="assessment_submissions",
    )
    op.drop_index(
        "ix_assessment_submissions_org_submitted_at",
        table_name="assessment_submissions",
    )
    op.drop_index(
        "ix_assessment_submissions_user_submitted_at",
        table_name="assessment_submissions",
    )
    op.drop_table("assessment_submissions")
