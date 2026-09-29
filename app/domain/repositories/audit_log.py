from abc import ABC, abstractmethod
import uuid

from app.domain.entities.audit_log import AuditLog


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
