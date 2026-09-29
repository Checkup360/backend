import uuid

from app.application.dto.audit_log import OrganizationComplianceSummaryDTO
from app.domain.exceptions import OrganizationNotFoundError
from app.domain.repositories.audit_log import AuditLogRepository
from app.domain.repositories.membership import MembershipRepository
from app.domain.repositories.organization import OrganizationRepository


class GetOrganizationComplianceSummaryUseCase:
    """Use case to calculate aggregated compliance and audit metrics for an organization."""

    def __init__(
        self,
        audit_log_repository: AuditLogRepository,
        organization_repository: OrganizationRepository,
        membership_repository: MembershipRepository,
    ) -> None:
        self._audit_log_repository = audit_log_repository
        self._organization_repository = organization_repository
        self._membership_repository = membership_repository

    async def execute(
        self,
        organization_id: uuid.UUID,
    ) -> OrganizationComplianceSummaryDTO:
        org = await self._organization_repository.get(organization_id)
        if org is None:
            raise OrganizationNotFoundError()

        stats = await self._audit_log_repository.get_compliance_stats(organization_id)

        # Count total members enrolled in the organization
        total_members = (
            await self._membership_repository.count_members_for_organization(
                organization_id
            )
        )

        return OrganizationComplianceSummaryDTO(
            total_audit_events=stats.get("total_audit_events", 0),
            consent_accepted_count=stats.get("consent_accepted_count", 0),
            consent_revoked_count=stats.get("consent_revoked_count", 0),
            data_exported_count=stats.get("data_exported_count", 0),
            audited_members_count=stats.get(
                "audited_members_count",
                min(total_members, stats.get("audited_members_count", 0)),
            ),
            actions_breakdown=stats.get("actions_breakdown", {}),
        )
