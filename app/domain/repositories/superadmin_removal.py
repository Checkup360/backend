from abc import ABC, abstractmethod
import uuid

from app.domain.entities.superadmin_removal import (
    RemovalRequestStatus,
    SuperadminRemovalRequest,
    SuperadminRemovalVote,
)


class SuperadminRemovalRepository(ABC):
    @abstractmethod
    async def create_request(
        self, request: SuperadminRemovalRequest
    ) -> SuperadminRemovalRequest:
        pass

    @abstractmethod
    async def get_request_by_id(
        self, request_id: uuid.UUID
    ) -> SuperadminRemovalRequest | None:
        pass

    @abstractmethod
    async def get_active_request_for_target(
        self, organization_id: uuid.UUID, target_user_id: uuid.UUID
    ) -> SuperadminRemovalRequest | None:
        pass

    @abstractmethod
    async def list_requests_for_organization(
        self,
        organization_id: uuid.UUID,
        status: str | None = None,
        page: int | None = None,
        page_size: int = 10,
    ) -> tuple[list[SuperadminRemovalRequest], int]:
        pass

    @abstractmethod
    async def update_request_status(
        self, request_id: uuid.UUID, status: RemovalRequestStatus
    ) -> None:
        pass

    @abstractmethod
    async def add_vote(self, vote: SuperadminRemovalVote) -> SuperadminRemovalVote:
        pass

    @abstractmethod
    async def get_vote(
        self, request_id: uuid.UUID, voter_user_id: uuid.UUID
    ) -> SuperadminRemovalVote | None:
        pass
