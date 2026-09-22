from datetime import datetime, timezone
import uuid

from app.domain.entities.superadmin_removal import (
    RemovalRequestStatus,
    SuperadminRemovalRequest,
    SuperadminRemovalVote,
    VoteDecision,
)
from app.domain.exceptions import (
    AlreadyVotedError,
    RemovalRequestAlreadyResolvedError,
    RemovalRequestNotFoundError,
    SelfVotingForbiddenError,
    VoterNotSuperadminError,
)
from app.domain.repositories import (
    MembershipRepository,
    RefreshTokenRepository,
)
from app.domain.repositories.superadmin_removal import (
    SuperadminRemovalRepository,
)
from app.domain.services.superadmin_quorum import SuperadminQuorumService
from app.domain.value_objects import OrgRole


class VoteSuperadminRemovalRequestUseCase:
    def __init__(
        self,
        membership_repo: MembershipRepository,
        removal_repo: SuperadminRemovalRepository,
        refresh_token_repo: RefreshTokenRepository,
    ):
        self.membership_repo = membership_repo
        self.removal_repo = removal_repo
        self.refresh_token_repo = refresh_token_repo

    async def execute(
        self,
        actor_user_id: uuid.UUID,
        actor_is_superuser: bool,
        organization_id: uuid.UUID,
        request_id: uuid.UUID,
        decision: VoteDecision,
    ) -> SuperadminRemovalRequest:
        request = await self.removal_repo.get_request_by_id(request_id)
        if not request or request.organization_id != organization_id:
            raise RemovalRequestNotFoundError()

        if request.status != RemovalRequestStatus.PENDING:
            raise RemovalRequestAlreadyResolvedError(
                "Removal request is already resolved"
            )

        if actor_user_id == request.target_user_id:
            raise SelfVotingForbiddenError(
                "Target superadmin cannot vote on their own removal"
            )

        if not actor_is_superuser:
            voter_membership = await self.membership_repo.get_by_user_and_org(
                actor_user_id, organization_id
            )
            if not voter_membership or OrgRole.SUPERADMIN not in voter_membership.roles:
                raise VoterNotSuperadminError(
                    "Only superadmins can vote on removal requests"
                )

        existing_vote = await self.removal_repo.get_vote(request_id, actor_user_id)
        if existing_vote:
            raise AlreadyVotedError("User has already voted on this request")

        now = datetime.now(timezone.utc)
        vote = SuperadminRemovalVote(
            id=uuid.uuid4(),
            request_id=request_id,
            voter_user_id=actor_user_id,
            decision=decision,
            voted_at=now,
        )
        await self.removal_repo.add_vote(vote)
        request.votes.append(vote)

        total_superadmins = await self.membership_repo.count_superadmins(
            organization_id
        )
        new_status = SuperadminQuorumService.evaluate_status(request, total_superadmins)

        if new_status != request.status:
            await self.removal_repo.update_request_status(request.id, new_status)
            request.status = new_status
            if new_status == RemovalRequestStatus.APPROVED:
                target_membership = await self.membership_repo.get_by_user_and_org(
                    request.target_user_id, organization_id
                )
                if target_membership:
                    target_membership.roles = [
                        r for r in target_membership.roles if r != OrgRole.SUPERADMIN
                    ]
                    await self.membership_repo.save(target_membership)
                    await self.refresh_token_repo.revoke_all_for_user(
                        request.target_user_id
                    )

        return request
