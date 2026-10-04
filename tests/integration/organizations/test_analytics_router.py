from datetime import datetime, timezone
import uuid
import pytest
from sqlalchemy import select

from app.domain.value_objects.org_role import OrgRole
from app.infrastructure.persistence.models import (
    Department,
    Organization,
    RiskScoreModel,
)


class TestOrganizationAnalyticsRouter:
    @pytest.mark.asyncio
    async def test_get_organization_risk_trends(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        user = await auth_scenario.register_and_login(
            email="org-analytics-admin@example.com",
            memberships=[("analytics-org", OrgRole.ADMIN)],
        )

        async with db_session_maker() as session:
            org = await session.scalar(
                select(Organization).where(Organization.slug == "analytics-org")
            )

            # Insert all required risk scores for employee in this org (Diabetes, Sleep Apnea, Depression)
            now = datetime.now(timezone.utc)
            session.add_all(
                [
                    RiskScoreModel(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        score_name="Diabetes",
                        risk_level="Low",
                        raw_value=5.0,
                        health_index=85.0,
                        explanation="Low risk",
                        contributing_factors={},
                        evaluated_at=now,
                    ),
                    RiskScoreModel(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        score_name="Sleep Apnea",
                        risk_level="Low",
                        raw_value=2.0,
                        health_index=85.0,
                        explanation="Low risk",
                        contributing_factors={},
                        evaluated_at=now,
                    ),
                    RiskScoreModel(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        score_name="Depression",
                        risk_level="Low",
                        raw_value=1.0,
                        health_index=85.0,
                        explanation="Low risk",
                        contributing_factors={},
                        evaluated_at=now,
                    ),
                ]
            )
            await session.commit()

        # Call analytics trends endpoint
        res = client.get(f"/organizations/{org.id}/analytics/trends?months=12")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        assert "period" in data[0]
        assert "month_label" in data[0]
        assert "average_score" in data[0]
        assert data[0]["average_score"] == 85.0

    @pytest.mark.asyncio
    async def test_get_organization_department_analytics(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="org-dept-analytics-admin@example.com",
            memberships=[("dept-analytics-org", OrgRole.ADMIN)],
        )

        async with db_session_maker() as session:
            org = await session.scalar(
                select(Organization).where(Organization.slug == "dept-analytics-org")
            )

            # Create a department
            dept = Department(
                id=uuid.uuid4(),
                organization_id=org.id,
                name="Engineering",
                slug="engineering",
            )
            session.add(dept)
            await session.commit()

        # Assign member to department
        emp = await make_user(email="dept.worker@example.com")
        await make_membership(
            user_id=emp.id,
            organization_id=org.id,
            role="member",
            department_id=dept.id,
        )

        async with db_session_maker() as session:
            now = datetime.now(timezone.utc)
            session.add_all(
                [
                    RiskScoreModel(
                        id=uuid.uuid4(),
                        user_id=emp.id,
                        score_name="Diabetes",
                        risk_level="High risk",
                        raw_value=18.0,
                        health_index=25.0,
                        explanation="High risk",
                        contributing_factors={},
                        evaluated_at=now,
                    ),
                    RiskScoreModel(
                        id=uuid.uuid4(),
                        user_id=emp.id,
                        score_name="Sleep Apnea",
                        risk_level="High risk",
                        raw_value=6.0,
                        health_index=25.0,
                        explanation="High risk",
                        contributing_factors={},
                        evaluated_at=now,
                    ),
                    RiskScoreModel(
                        id=uuid.uuid4(),
                        user_id=emp.id,
                        score_name="Depression",
                        risk_level="High risk",
                        raw_value=15.0,
                        health_index=25.0,
                        explanation="High risk",
                        contributing_factors={},
                        evaluated_at=now,
                    ),
                ]
            )
            await session.commit()

        res = client.get(f"/organizations/{org.id}/analytics/departments")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["name"] == "Engineering"
        assert data[0]["average_score"] == 25.0
        assert data[0]["total_workers"] == 1
        assert data[0]["high_risk_count"] == 1

    @pytest.mark.asyncio
    async def test_get_organization_department_analytics_partial_scores_calculates_average(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="org-dept-partial-admin@example.com",
            memberships=[("dept-partial-org", OrgRole.ADMIN)],
        )

        async with db_session_maker() as session:
            org = await session.scalar(
                select(Organization).where(Organization.slug == "dept-partial-org")
            )
            dept = Department(
                id=uuid.uuid4(),
                organization_id=org.id,
                name="Marketing",
                slug="marketing",
            )
            session.add(dept)
            await session.commit()

        emp = await make_user(email="dept.partial.worker@example.com")
        await make_membership(
            user_id=emp.id,
            organization_id=org.id,
            role="member",
            department_id=dept.id,
        )

        async with db_session_maker() as session:
            # Only Diabetes submitted, missing Sleep Apnea and Depression
            session.add(
                RiskScoreModel(
                    id=uuid.uuid4(),
                    user_id=emp.id,
                    score_name="Diabetes",
                    risk_level="Moderate risk",
                    raw_value=18.0,
                    health_index=50.0,
                    explanation="Moderate risk",
                    contributing_factors={},
                    evaluated_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        res = client.get(f"/organizations/{org.id}/analytics/departments")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["name"] == "Marketing"
        assert data[0]["average_score"] == 50.0
        assert data[0]["total_workers"] == 1
        assert data[0]["high_risk_count"] == 0

    @pytest.mark.asyncio
    async def test_analytics_unauthorized_member(
        self,
        client,
        db_session_maker,
        auth_scenario,
    ):
        await auth_scenario.register_and_login(
            email="member-only@example.com",
            memberships=[("member-only-org", OrgRole.MEMBER)],
        )

        async with db_session_maker() as session:
            org = await session.scalar(
                select(Organization).where(Organization.slug == "member-only-org")
            )

        res_trends = client.get(f"/organizations/{org.id}/analytics/trends")
        assert res_trends.status_code == 403

        res_depts = client.get(f"/organizations/{org.id}/analytics/departments")
        assert res_depts.status_code == 403
