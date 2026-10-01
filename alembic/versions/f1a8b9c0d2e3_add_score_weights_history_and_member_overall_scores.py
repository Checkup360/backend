"""add organization score weights and member overall scores

Revision ID: f1a8b9c0d2e3
Revises: c94f9837ab18
Create Date: 2026-09-18 14:15:00.000000

"""

from datetime import datetime, timezone
import json
from typing import Any, Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# The backfill logic below is a frozen snapshot of the scoring rules as they
# were at this revision, when scores were stored as risk values (0 = lowest
# risk, 100 = highest risk). Migrations must not import application code:
# later changes to the live rules would silently alter this historical step.
_DEFAULT_SCORE_WEIGHTS: dict[str, float] = {
    "diabetes": 34.0,
    "sleep_apnea": 33.0,
    "depression": 33.0,
}


def _normalize_score_key(score_name: str) -> str:
    lower = score_name.lower()
    if "findrisc" in lower or "diabetes" in lower:
        return "diabetes"
    if "stop" in lower or "sleep" in lower:
        return "sleep_apnea"
    if (
        "phq" in lower
        or "depression" in lower
        or "mood" in lower
        or "emotional" in lower
    ):
        return "depression"
    if "metabolic" in lower:
        return "metabolic_syndrome"
    if "eoss" in lower or "obesity" in lower:
        return "eoss"
    if "score2" in lower or "cardiovascular" in lower or "cardio" in lower:
        return "cardiovascular"
    if (
        "nordic" in lower
        or "nmq" in lower
        or "ergonomics" in lower
        or "musculoskeletal" in lower
    ):
        return "nordic_nmq"
    if "audit" in lower or "alcohol" in lower:
        return "audit_c"
    if "pss" in lower or "stress" in lower:
        return "pss10"
    return lower.replace(" ", "_").replace("-", "_")


def _calculate_weighted_overall_score(
    results: list[Any],
    weights: dict[str, float] | None = None,
) -> tuple[float | None, str | None]:
    if not results:
        return None, None

    latest_by_key: dict[str, Any] = {}
    for r in results:
        key = _normalize_score_key(getattr(r, "score_name", "") or "")
        existing = latest_by_key.get(key)
        if existing is None:
            latest_by_key[key] = r
            continue
        existing_time = getattr(existing, "evaluated_at", None)
        current_time = getattr(r, "evaluated_at", None)
        if current_time and existing_time and current_time > existing_time:
            latest_by_key[key] = r

    active_weights = weights if weights else _DEFAULT_SCORE_WEIGHTS
    score_entries: list[tuple[float, float]] = []
    for key, weight in active_weights.items():
        if weight <= 0:
            continue
        if key not in latest_by_key:
            return None, None
        value = getattr(latest_by_key[key], "normalized_value", None)
        if value is None:
            return None, None
        score_entries.append((float(value), float(weight)))

    if not score_entries:
        return None, None

    total_weight = sum(weight for _, weight in score_entries)
    overall_score = round(
        sum(value * weight for value, weight in score_entries) / total_weight, 1
    )

    if overall_score <= 20:
        return overall_score, "Low risk"
    if overall_score <= 50:
        return overall_score, "Moderate risk"
    return overall_score, "Needs attention"


# revision identifiers, used by Alembic.
revision: str = "f1a8b9c0d2e3"
down_revision: Union[str, Sequence[str], None] = "c94f9837ab18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. organization_score_weights table
    op.create_table(
        "organization_score_weights",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"], ["user.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "version", name="uq_org_score_weights_org_version"
        ),
    )
    op.create_index(
        "ix_organization_score_weights_organization_id",
        "organization_score_weights",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_score_weights_created_at",
        "organization_score_weights",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "idx_org_score_weights_lookup",
        "organization_score_weights",
        ["organization_id", "version"],
        unique=False,
    )

    # 2. member_overall_scores table
    op.create_table(
        "member_overall_scores",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score_weights_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=100), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["score_weights_id"],
            ["organization_score_weights.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["assessment_submissions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_member_overall_scores_user_id",
        "member_overall_scores",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_member_overall_scores_organization_id",
        "member_overall_scores",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_member_overall_scores_score_weights_id",
        "member_overall_scores",
        ["score_weights_id"],
        unique=False,
    )
    op.create_index(
        "ix_member_overall_scores_submission_id",
        "member_overall_scores",
        ["submission_id"],
        unique=False,
    )
    op.create_index(
        "ix_member_overall_scores_evaluated_at",
        "member_overall_scores",
        ["evaluated_at"],
        unique=False,
    )
    op.create_index(
        "idx_member_overall_scores_user_evaluated",
        "member_overall_scores",
        ["user_id", "evaluated_at"],
        unique=False,
    )
    op.create_index(
        "idx_member_overall_scores_org_evaluated",
        "member_overall_scores",
        ["organization_id", "evaluated_at"],
        unique=False,
    )

    # 3. Backfill organization_score_weights v1 for existing organizations
    bind = op.get_bind()
    try:
        orgs_rows = bind.execute(
            sa.text("SELECT id, score_weights, created_at FROM organizations")
        ).fetchall()
    except Exception:
        orgs_rows = []

    org_weights_map: dict[uuid.UUID, tuple[uuid.UUID, dict[str, float]]] = {}
    for org_row in orgs_rows:
        org_id = org_row[0]
        if isinstance(org_id, str):
            org_id = uuid.UUID(org_id)
        raw_weights = org_row[1]
        created_at = org_row[2] or datetime.now(timezone.utc)
        if isinstance(raw_weights, str):
            try:
                custom_weights = json.loads(raw_weights)
            except Exception:
                custom_weights = None
        else:
            custom_weights = raw_weights

        weights_dict = (
            custom_weights
            if isinstance(custom_weights, dict) and custom_weights
            else dict(_DEFAULT_SCORE_WEIGHTS)
        )
        weights_id = uuid.uuid4()
        bind.execute(
            sa.text(
                "INSERT INTO organization_score_weights (id, organization_id, version, weights, changed_by_user_id, created_at) "
                "VALUES (:id, :org_id, 1, :weights, NULL, :created_at)"
            ),
            {
                "id": str(weights_id),
                "org_id": str(org_id),
                "weights": json.dumps(weights_dict),
                "created_at": created_at,
            },
        )
        org_weights_map[org_id] = (weights_id, weights_dict)

    # 4. Backfill member_overall_scores for existing memberships with risk scores
    if org_weights_map:
        try:
            memberships_rows = bind.execute(
                sa.text("SELECT user_id, organization_id FROM memberships")
            ).fetchall()
        except Exception:
            memberships_rows = []

        for mem_row in memberships_rows:
            u_id = mem_row[0]
            o_id = mem_row[1]
            if isinstance(u_id, str):
                u_id = uuid.UUID(u_id)
            if isinstance(o_id, str):
                o_id = uuid.UUID(o_id)

            if o_id not in org_weights_map:
                continue

            weights_id, weights_dict = org_weights_map[o_id]

            try:
                scores_rows = bind.execute(
                    sa.text(
                        "SELECT score_name, risk_level, raw_value, normalized_value, submission_id, evaluated_at "
                        "FROM risk_scores WHERE user_id = :user_id ORDER BY evaluated_at ASC"
                    ),
                    {"user_id": str(u_id)},
                ).fetchall()
            except Exception:
                scores_rows = []

            if not scores_rows:
                continue

            # Group scores into evaluation moments/submissions
            class MockScore:
                def __init__(
                    self,
                    score_name,
                    risk_level,
                    raw_value,
                    normalized_value,
                    evaluated_at,
                ):
                    self.score_name = score_name
                    self.risk_level = risk_level
                    self.raw_value = raw_value
                    self.normalized_value = normalized_value
                    self.evaluated_at = evaluated_at

            # Build overall score for user's latest scores
            score_objects = [
                MockScore(r[0], r[1], r[2], r[3], r[5]) for r in scores_rows
            ]
            overall_score, overall_risk_level = _calculate_weighted_overall_score(
                score_objects, weights_dict
            )

            if overall_score is not None and overall_risk_level is not None:
                latest_eval_at = scores_rows[-1][5] or datetime.now(timezone.utc)
                latest_sub_id = scores_rows[-1][4]
                bind.execute(
                    sa.text(
                        "INSERT INTO member_overall_scores (id, user_id, organization_id, score_weights_id, submission_id, overall_score, risk_level, evaluated_at) "
                        "VALUES (:id, :user_id, :org_id, :score_weights_id, :submission_id, :overall_score, :risk_level, :evaluated_at)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": str(u_id),
                        "org_id": str(o_id),
                        "score_weights_id": str(weights_id),
                        "submission_id": str(latest_sub_id) if latest_sub_id else None,
                        "overall_score": overall_score,
                        "risk_level": overall_risk_level,
                        "evaluated_at": latest_eval_at,
                    },
                )


def downgrade() -> None:
    op.drop_table("member_overall_scores")
    op.drop_table("organization_score_weights")
