from typing import Protocol
import uuid

from app.domain.entities.analytics import (
    DepartmentAnalyticsSummary,
    OrganizationRegistrationTrendPoint,
    OrganizationRiskTrendPoint,
)


class AnalyticsRepository(Protocol):
    async def get_organization_trends(
        self,
        organization_id: uuid.UUID,
        months: int = 12,
        department_id: uuid.UUID | None = None,
    ) -> list[OrganizationRiskTrendPoint]: ...

    async def get_departments_summary(
        self, organization_id: uuid.UUID
    ) -> list[DepartmentAnalyticsSummary]: ...

    async def get_registration_trends(
        self, organization_id: uuid.UUID
    ) -> list[OrganizationRegistrationTrendPoint]: ...
