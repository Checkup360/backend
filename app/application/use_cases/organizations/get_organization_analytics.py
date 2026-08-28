import uuid

from app.domain.entities.analytics import (
    DepartmentAnalyticsSummary,
    OrganizationRiskTrendPoint,
)
from app.domain.exceptions import OrganizationNotFoundError
from app.domain.repositories.analytics import AnalyticsRepository
from app.domain.repositories.organization import OrganizationRepository


class GetOrganizationAnalyticsUseCase:
    def __init__(
        self,
        analytics_repo: AnalyticsRepository,
        organization_repo: OrganizationRepository,
    ) -> None:
        self._analytics_repo = analytics_repo
        self._org_repo = organization_repo

    async def get_trends(
        self,
        organization_id: uuid.UUID,
        months: int = 12,
        department_id: uuid.UUID | None = None,
    ) -> list[OrganizationRiskTrendPoint]:
        org = await self._org_repo.get(organization_id)
        if not org:
            raise OrganizationNotFoundError()

        return await self._analytics_repo.get_organization_trends(
            organization_id=organization_id,
            months=months,
            department_id=department_id,
        )

    async def get_departments_summary(
        self, organization_id: uuid.UUID
    ) -> list[DepartmentAnalyticsSummary]:
        org = await self._org_repo.get(organization_id)
        if not org:
            raise OrganizationNotFoundError()

        return await self._analytics_repo.get_departments_summary(organization_id)
