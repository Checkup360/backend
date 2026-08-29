from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.analytics import (
    DepartmentAnalyticsSummary,
    OrganizationRiskTrendPoint,
)
from app.domain.repositories.analytics import AnalyticsRepository
from app.infrastructure.persistence.models.department import Department
from app.infrastructure.persistence.models.membership import Membership
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

        period_col = func.to_char(RiskScoreModel.evaluated_at, "YYYY-MM").label(
            "period"
        )
        month_label_col = func.to_char(RiskScoreModel.evaluated_at, "Mon").label(
            "month_label"
        )
        avg_score_col = func.avg(RiskScoreModel.normalized_value).label("avg_score")
        total_assessments_col = func.count(distinct(RiskScoreModel.id)).label(
            "total_assessments"
        )

        query = (
            select(
                period_col,
                month_label_col,
                avg_score_col,
                total_assessments_col,
            )
            .join(Membership, Membership.user_id == RiskScoreModel.user_id)
            .where(
                Membership.organization_id == organization_id,
                RiskScoreModel.normalized_value.isnot(None),
                RiskScoreModel.evaluated_at >= cutoff_date,
            )
        )

        if department_id is not None:
            query = query.where(Membership.department_id == department_id)

        query = query.group_by(period_col, month_label_col).order_by(period_col.asc())

        result = await self._db.execute(query)
        rows = result.all()

        # Query scores broken down by study name
        study_query = (
            select(
                period_col,
                RiskScoreModel.score_name,
                avg_score_col,
            )
            .join(Membership, Membership.user_id == RiskScoreModel.user_id)
            .where(
                Membership.organization_id == organization_id,
                RiskScoreModel.normalized_value.isnot(None),
                RiskScoreModel.evaluated_at >= cutoff_date,
            )
        )
        if department_id is not None:
            study_query = study_query.where(Membership.department_id == department_id)

        study_query = study_query.group_by(period_col, RiskScoreModel.score_name)
        study_result = await self._db.execute(study_query)
        study_rows = study_result.all()

        study_map: dict[str, dict[str, float]] = {}
        for s_row in study_rows:
            p_key = str(s_row.period)
            if p_key not in study_map:
                study_map[p_key] = {}
            s_name = str(s_row.score_name)
            s_avg = float(s_row.avg_score) if s_row.avg_score is not None else 0.0
            study_map[p_key][s_name] = round(s_avg, 1)

        points: list[OrganizationRiskTrendPoint] = []
        for row in rows:
            p_str = str(row.period)
            avg_score = float(row.avg_score) if row.avg_score is not None else 0.0
            risk_index = round(max(0.0, 100.0 - avg_score), 1)
            points.append(
                OrganizationRiskTrendPoint(
                    period=p_str,
                    month_label=str(row.month_label),
                    average_score=avg_score,
                    risk_index=risk_index,
                    total_assessments=int(row.total_assessments),
                    scores_by_study=study_map.get(p_str, {}),
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
                        average_score=100.0,
                        total_workers=0,
                        high_risk_count=0,
                    )
                )
                continue

            # Query scores for these users
            scores_query = select(
                RiskScoreModel.user_id,
                RiskScoreModel.normalized_value,
                RiskScoreModel.risk_level,
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
                        average_score=100.0,
                        total_workers=total_workers,
                        high_risk_count=0,
                    )
                )
                continue

            # Calculate average score and count high risk users
            normalized_values = [
                float(row.normalized_value)
                for row in scores_rows
                if row.normalized_value is not None
            ]
            avg_score = (
                round(sum(normalized_values) / len(normalized_values), 1)
                if normalized_values
                else 100.0
            )

            # High risk users: users whose normalized_value < 60 or risk_level indicates high risk
            high_risk_users = {
                row.user_id
                for row in scores_rows
                if (
                    row.normalized_value is not None
                    and float(row.normalized_value) < 60.0
                )
                or (row.risk_level and "high" in row.risk_level.lower())
            }

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
