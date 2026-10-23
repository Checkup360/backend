from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
import uuid

from app.domain.entities.audit_log import AuditLog
from app.domain.value_objects import AuditLogSortField, SortDirection


class AuditLogRepository(ABC):
    @abstractmethod
    async def log(self, audit_log: AuditLog) -> AuditLog:
        """Persists a new immutable audit log entry."""
        ...

    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Retrieves audit entries for a specific user, newest first."""
        ...

    @abstractmethod
    async def get_by_organization_id(
        self,
        organization_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Retrieves audit entries for a specific organization, newest first."""
        ...

    @abstractmethod
    async def list_by_organization(
        self,
        organization_id: uuid.UUID,
        action: str | None = None,
        user_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: AuditLogSortField | None = None,
        sort_direction: SortDirection = SortDirection.DESC,
    ) -> tuple[list[AuditLog], int]:
        """Lists audit entries for an organization with optional filters and total count."""
        ...

    @abstractmethod
    async def list_all(
        self,
        action: str | None = None,
        organization_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Lists all system audit entries with optional filters and total count."""
        ...

    @abstractmethod
    async def get_compliance_stats(
        self,
        organization_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Calculates aggregated compliance and audit statistics for an organization."""
        ...
