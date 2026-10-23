from datetime import datetime
import uuid

from app.application.dto.audit_log import AuditLogEntryDTO, AuditLogListDTO
from app.domain.exceptions import OrganizationNotFoundError
from app.domain.repositories.audit_log import AuditLogRepository
from app.domain.repositories.member_details import MemberDetailsRepository
from app.domain.repositories.organization import OrganizationRepository
from app.domain.repositories.user import UserRepository
from app.domain.value_objects import AuditLogSortField, SortDirection


class GetOrganizationAuditLogsUseCase:
    """Use case to list audit logs for a specific organization with filtering and pagination."""

    def __init__(
        self,
        audit_log_repository: AuditLogRepository,
        organization_repository: OrganizationRepository,
        user_repository: UserRepository,
        member_details_repository: MemberDetailsRepository,
    ) -> None:
        self._audit_log_repository = audit_log_repository
        self._organization_repository = organization_repository
        self._user_repository = user_repository
        self._member_details_repository = member_details_repository

    async def execute(
        self,
        organization_id: uuid.UUID,
        action: str | None = None,
        user_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        sort_by: AuditLogSortField | None = None,
        sort_direction: SortDirection = SortDirection.DESC,
        page: int = 1,
        page_size: int = 50,
    ) -> AuditLogListDTO:
        org = await self._organization_repository.get(organization_id)
        if org is None:
            raise OrganizationNotFoundError()

        page = max(1, page)
        page_size = max(1, min(100, page_size))
        offset = (page - 1) * page_size

        logs, total = await self._audit_log_repository.list_by_organization(
            organization_id=organization_id,
            action=action,
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            limit=page_size,
            offset=offset,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

        # Collect unique user IDs to batch-enrich user details
        user_ids = {log.user_id for log in logs if log.user_id is not None}
        users_map: dict[uuid.UUID, str] = {}
        names_map: dict[uuid.UUID, str] = {}

        for uid in user_ids:
            u = await self._user_repository.get(uid)
            if u:
                users_map[uid] = u.email
            details = await self._member_details_repository.get_by_user(uid)
            if details and (details.first_name or details.last_name):
                full_name = (
                    f"{details.first_name or ''} {details.last_name or ''}".strip()
                )
                if full_name:
                    names_map[uid] = full_name

        dtos: list[AuditLogEntryDTO] = []
        for log in logs:
            dtos.append(
                AuditLogEntryDTO(
                    id=log.id,
                    user_id=log.user_id,
                    organization_id=log.organization_id,
                    action=log.action,
                    resource_type=log.resource_type,
                    resource_id=log.resource_id,
                    details=log.details,
                    created_at=log.created_at,
                    user_email=users_map.get(log.user_id) if log.user_id else None,
                    user_name=names_map.get(log.user_id) if log.user_id else None,
                )
            )

        has_next = (offset + len(logs)) < total

        return AuditLogListDTO(
            items=dtos,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next,
        )
