from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.analytics import (
    DepartmentAnalyticsSummary,
    OrganizationRegistrationTrendPoint,
    OrganizationRiskTrendPoint,
)
from app.domain.repositories.analytics import AnalyticsRepository
from app.domain.services.risk_score_calculator import calculate_weighted_overall_score
from app.infrastructure.persistence.models.department import Department
from app.infrastructure.persistence.models.membership import Membership
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.models.risk_score import RiskScoreModel


class AnalyticsRepositoryImpl(AnalyticsRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_organization_trends(
        self,
        organization_id: UUID,
        months: int = 12,
        department_id: UUID | None = None,
    ) -> list[OrganizationRiskTrendPoint]:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=months * 31)

        # Fetch org score weights if configured
        org_query = select(Organization.score_weights).where(
            Organization.id == organization_id
        )
        org_res = await self._db.execute(org_query)
        score_weights = org_res.scalar_one_or_none()

        period_col = func.to_char(RiskScoreModel.evaluated_at, "YYYY-MM").label(
            "period"
        )
        month_label_col = func.to_char(RiskScoreModel.evaluated_at, "Mon").label(
            "month_label"
        )

        # Fetch raw scores to compute both per-study and overall scores cumulatively
        # (Latest score for each user per study carries over into subsequent periods)
        scores_query = (
            select(
                period_col,
                month_label_col,
                RiskScoreModel.user_id,
                RiskScoreModel.score_name,
                RiskScoreModel.normalized_value,
                RiskScoreModel.evaluated_at,
            )
            .join(Membership, Membership.user_id == RiskScoreModel.user_id)
            .where(
                Membership.organization_id == organization_id,
                RiskScoreModel.normalized_value.isnot(None),
                RiskScoreModel.evaluated_at >= cutoff_date,
            )
        )
        if department_id is not None:
            scores_query = scores_query.where(Membership.department_id == department_id)

        scores_query = scores_query.order_by(
            period_col.asc(), RiskScoreModel.evaluated_at.asc()
        )
        scores_res = await self._db.execute(scores_query)
        all_rows = scores_res.all()

        periods: list[str] = []
        period_month_labels: dict[str, str] = {}
        period_assessments_count: dict[str, int] = {}
        user_scores_by_period: dict[str, dict[UUID, list[Any]]] = {}

        for r in all_rows:
            p_key = str(r.period)
            if p_key not in period_month_labels:
                periods.append(p_key)
                period_month_labels[p_key] = str(r.month_label)
                period_assessments_count[p_key] = 0
                user_scores_by_period[p_key] = {}
            period_assessments_count[p_key] += 1
            user_scores_by_period[p_key].setdefault(r.user_id, []).append(r)

        cumulative_user_scores: dict[UUID, list[Any]] = {}
        points: list[OrganizationRiskTrendPoint] = []

        for p_key in periods:
            for u_id, u_rows in user_scores_by_period[p_key].items():
                cumulative_user_scores.setdefault(u_id, []).extend(u_rows)

            # Compute latest score per study across all members up to this period
            # (user_id, study_name) -> latest normalized_value
            latest_study_by_user: dict[str, dict[UUID, float]] = {}
            for u_id, all_u_rows in cumulative_user_scores.items():
                # Sort this user's rows by evaluated_at
                sorted_u_rows = sorted(
                    all_u_rows,
                    key=lambda x: getattr(x, "evaluated_at", None) or datetime.min,
                )
                for r in sorted_u_rows:
                    s_name = str(r.score_name)
                    if s_name:
                        latest_study_by_user.setdefault(s_name, {})[u_id] = float(
                            r.normalized_value
                        )

            # Average per study in this period
            period_study_scores: dict[str, float] = {}
            for s_name, user_values in latest_study_by_user.items():
                if user_values:
                    period_study_scores[s_name] = round(
                        sum(user_values.values()) / len(user_values), 1
                    )

            # Compute overall score for users who have completed all required assessments
            period_overall_scores: list[float] = []
            for u_id, all_u_rows in cumulative_user_scores.items():
                u_score, _ = calculate_weighted_overall_score(
                    all_u_rows, weights=score_weights
                )
                if u_score is not None:
                    period_overall_scores.append(u_score)

            if period_overall_scores:
                avg_score = round(
                    sum(period_overall_scores) / len(period_overall_scores), 1
                )
                risk_index = avg_score
            else:
                avg_score = None
                risk_index = None

            points.append(
                OrganizationRiskTrendPoint(
                    period=p_key,
                    month_label=period_month_labels[p_key],
                    average_score=avg_score,
                    risk_index=risk_index,
                    total_assessments=period_assessments_count[p_key],
                    scores_by_study=period_study_scores,
                )
            )

        return points

    async def get_departments_summary(
        self, organization_id: UUID
    ) -> list[DepartmentAnalyticsSummary]:
        # 1. Fetch all departments for this organization
        depts_query = (
            select(Department)
            .where(Department.organization_id == organization_id)
            .order_by(Department.name.asc())
        )
        depts_result = await self._db.execute(depts_query)
        departments = depts_result.scalars().all()

        if not departments:
            return []

        # Fetch org score weights if configured
        org_query = select(Organization.score_weights).where(
            Organization.id == organization_id
        )
        org_res = await self._db.execute(org_query)
        score_weights = org_res.scalar_one_or_none()

        summaries: list[DepartmentAnalyticsSummary] = []

        for dept in departments:
            # Query members in department
            members_query = select(Membership.user_id).where(
                Membership.organization_id == organization_id,
                Membership.department_id == dept.id,
            )
            members_res = await self._db.execute(members_query)
            user_ids = [row[0] for row in members_res.all()]

            total_workers = len(user_ids)
            if total_workers == 0:
                summaries.append(
                    DepartmentAnalyticsSummary(
                        department_id=dept.id,
                        name=dept.name,
                        average_score=None,
                        total_workers=0,
                        high_risk_count=0,
                    )
                )
                continue

            # Query scores for these users
            scores_query = select(
                RiskScoreModel.user_id,
                RiskScoreModel.score_name,
                RiskScoreModel.normalized_value,
                RiskScoreModel.risk_level,
                RiskScoreModel.evaluated_at,
            ).where(
                RiskScoreModel.user_id.in_(user_ids),
                RiskScoreModel.normalized_value.isnot(None),
            )
            scores_res = await self._db.execute(scores_query)
            scores_rows = scores_res.all()

            if not scores_rows:
                summaries.append(
                    DepartmentAnalyticsSummary(
                        department_id=dept.id,
                        name=dept.name,
                        average_score=None,
                        total_workers=total_workers,
                        high_risk_count=0,
                    )
                )
                continue

            # Group scores by user
            user_scores_map: dict[UUID, list[Any]] = {}
            for row in scores_rows:
                user_scores_map.setdefault(row.user_id, []).append(row)

            user_overall_scores: list[float] = []
            high_risk_users: set[UUID] = set()

            for u_id, u_scores in user_scores_map.items():
                u_score, u_risk = calculate_weighted_overall_score(
                    u_scores, weights=score_weights
                )
                if u_score is not None:
                    user_overall_scores.append(u_score)
                    if u_score > 50.0 or (
                        u_risk
                        and ("attention" in u_risk.lower() or "high" in u_risk.lower())
                    ):
                        high_risk_users.add(u_id)

            avg_score = (
                round(sum(user_overall_scores) / len(user_overall_scores), 1)
                if user_overall_scores
                else None
            )

            summaries.append(
                DepartmentAnalyticsSummary(
                    department_id=dept.id,
                    name=dept.name,
                    average_score=avg_score,
                    total_workers=total_workers,
                    high_risk_count=len(high_risk_users),
                )
            )

        return summaries

    async def get_registration_trends(
        self, organization_id: UUID
    ) -> list[OrganizationRegistrationTrendPoint]:
        period_col = func.to_char(Membership.created_at, "YYYY-MM-DD").label("period")
        date_label_col = func.to_char(Membership.created_at, "DD Mon").label(
            "date_label"
        )
        count_col = func.count().label("new_members")

        query = (
            select(
                period_col,
                date_label_col,
                count_col,
            )
            .where(Membership.organization_id == organization_id)
            .group_by(period_col, date_label_col)
            .order_by(period_col.asc())
        )

        result = await self._db.execute(query)
        rows = result.all()

        points: list[OrganizationRegistrationTrendPoint] = []
        cumulative = 0
        for row in rows:
            new_count = int(row.new_members)
            cumulative += new_count
            points.append(
                OrganizationRegistrationTrendPoint(
                    period=str(row.period),
                    date_label=str(row.date_label),
                    new_members=new_count,
                    cumulative_members=cumulative,
                )
            )

        return points
