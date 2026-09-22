from datetime import datetime, timezone
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities.superadmin_removal import (
    RemovalRequestStatus,
    SuperadminRemovalRequest,
    SuperadminRemovalVote,
    VoteDecision,
)
from app.domain.repositories.superadmin_removal import (
    SuperadminRemovalRepository,
)
from app.infrastructure.persistence.models.superadmin_removal import (
    SuperadminRemovalRequestModel,
    SuperadminRemovalVoteModel,
)


class SqlAlchemySuperadminRemovalRepository(SuperadminRemovalRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _to_vote_domain(
        orm: SuperadminRemovalVoteModel,
    ) -> SuperadminRemovalVote:
        return SuperadminRemovalVote(
            id=orm.id,
            request_id=orm.request_id,
            voter_user_id=orm.voter_user_id,
            decision=VoteDecision(orm.decision),
            voted_at=orm.voted_at,
        )

    @classmethod
    def _to_request_domain(
        cls, orm: SuperadminRemovalRequestModel
    ) -> SuperadminRemovalRequest:
        votes = [cls._to_vote_domain(v) for v in (orm.votes or [])]
        return SuperadminRemovalRequest(
            id=orm.id,
            organization_id=orm.organization_id,
            target_user_id=orm.target_user_id,
            requester_user_id=orm.requester_user_id,
            status=RemovalRequestStatus(orm.status),
            required_votes=orm.required_votes,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            reason=orm.reason,
            votes=votes,
        )

    async def create_request(
        self, request: SuperadminRemovalRequest
    ) -> SuperadminRemovalRequest:
        orm = SuperadminRemovalRequestModel(
            id=request.id,
            organization_id=request.organization_id,
            target_user_id=request.target_user_id,
            requester_user_id=request.requester_user_id,
            reason=request.reason,
            status=request.status.value,
            required_votes=request.required_votes,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )
        self.db.add(orm)
        await self.db.commit()
        await self.db.refresh(orm)
        return self._to_request_domain(orm)

    async def get_request_by_id(
        self, request_id: uuid.UUID
    ) -> SuperadminRemovalRequest | None:
        query = (
            select(SuperadminRemovalRequestModel)
            .options(selectinload(SuperadminRemovalRequestModel.votes))
            .where(SuperadminRemovalRequestModel.id == request_id)
        )
        result = await self.db.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_request_domain(orm) if orm else None

    async def get_active_request_for_target(
        self, organization_id: uuid.UUID, target_user_id: uuid.UUID
    ) -> SuperadminRemovalRequest | None:
        query = (
            select(SuperadminRemovalRequestModel)
            .options(selectinload(SuperadminRemovalRequestModel.votes))
            .where(
                SuperadminRemovalRequestModel.organization_id == organization_id,
                SuperadminRemovalRequestModel.target_user_id == target_user_id,
                SuperadminRemovalRequestModel.status
                == RemovalRequestStatus.PENDING.value,
            )
        )
        result = await self.db.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_request_domain(orm) if orm else None

    async def list_requests_for_organization(
        self,
        organization_id: uuid.UUID,
        status: RemovalRequestStatus | None = None,
    ) -> list[SuperadminRemovalRequest]:
        query = (
            select(SuperadminRemovalRequestModel)
            .options(selectinload(SuperadminRemovalRequestModel.votes))
            .where(
                SuperadminRemovalRequestModel.organization_id == organization_id,
            )
            .order_by(desc(SuperadminRemovalRequestModel.created_at))
        )
        if status:
            query = query.where(SuperadminRemovalRequestModel.status == status.value)
        result = await self.db.execute(query)
        return [self._to_request_domain(orm) for orm in result.scalars().all()]

    async def update_request_status(
        self, request_id: uuid.UUID, status: RemovalRequestStatus
    ) -> None:
        query = select(SuperadminRemovalRequestModel).where(
            SuperadminRemovalRequestModel.id == request_id
        )
        result = await self.db.execute(query)
        orm = result.scalar_one_or_none()
        if orm:
            orm.status = status.value
            orm.updated_at = datetime.now(timezone.utc)
            await self.db.commit()

    async def add_vote(self, vote: SuperadminRemovalVote) -> SuperadminRemovalVote:
        orm = SuperadminRemovalVoteModel(
            id=vote.id,
            request_id=vote.request_id,
            voter_user_id=vote.voter_user_id,
            decision=vote.decision.value,
            voted_at=vote.voted_at,
        )
        self.db.add(orm)
        await self.db.commit()
        await self.db.refresh(orm)
        return self._to_vote_domain(orm)

    async def get_vote(
        self, request_id: uuid.UUID, voter_user_id: uuid.UUID
    ) -> SuperadminRemovalVote | None:
        query = select(SuperadminRemovalVoteModel).where(
            SuperadminRemovalVoteModel.request_id == request_id,
            SuperadminRemovalVoteModel.voter_user_id == voter_user_id,
        )
        result = await self.db.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_vote_domain(orm) if orm else None
