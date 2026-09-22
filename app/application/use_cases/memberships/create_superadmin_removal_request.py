from datetime import datetime, timezone
import uuid

from app.domain.entities.superadmin_removal import (
    RemovalRequestStatus,
    SuperadminRemovalRequest,
    SuperadminRemovalVote,
    VoteDecision,
)
from app.domain.exceptions import (
    CannotRemoveLastSuperadminError,
    InsufficientRolePermissionError,
    MembershipNotFoundError,
    NotOrganizationAdminError,
    OrganizationNotFoundError,
    RemovalRequestAlreadyExistsError,
    SelfVotingForbiddenError,
)
from app.domain.repositories import (
    MembershipRepository,
    OrganizationRepository,
    RefreshTokenRepository,
)
from app.domain.repositories.superadmin_removal import (
    SuperadminRemovalRepository,
)
from app.domain.services.superadmin_quorum import SuperadminQuorumService
from app.domain.value_objects import OrgRole


class CreateSuperadminRemovalRequestUseCase:
    def __init__(
        self,
        membership_repo: MembershipRepository,
        org_repo: OrganizationRepository,
        removal_repo: SuperadminRemovalRepository,
        refresh_token_repo: RefreshTokenRepository,
    ):
        self.membership_repo = membership_repo
        self.org_repo = org_repo
        self.removal_repo = removal_repo
        self.refresh_token_repo = refresh_token_repo

    async def execute(
        self,
        actor_user_id: uuid.UUID,
        actor_is_superuser: bool,
        organization_id: uuid.UUID,
        target_user_id: uuid.UUID,
        reason: str | None = None,
    ) -> SuperadminRemovalRequest:
        organization = await self.org_repo.get(organization_id)
        if not organization:
            raise OrganizationNotFoundError()

        target_membership = await self.membership_repo.get_by_user_and_org(
            target_user_id, organization_id
        )
        if not target_membership:
            raise MembershipNotFoundError()

        if OrgRole.SUPERADMIN not in target_membership.roles:
            raise InsufficientRolePermissionError("Target user is not a superadmin")

        if not actor_is_superuser:
            if actor_user_id == target_user_id:
                raise SelfVotingForbiddenError("Cannot initiate removal of oneself")

            actor_membership = await self.membership_repo.get_by_user_and_org(
                actor_user_id, organization_id
            )
            if not actor_membership:
                raise NotOrganizationAdminError()

            if OrgRole.SUPERADMIN not in actor_membership.roles:
                raise InsufficientRolePermissionError(
                    "Only superadmins can initiate superadmin removal"
                )

        existing = await self.removal_repo.get_active_request_for_target(
            organization_id, target_user_id
        )
        if existing:
            raise RemovalRequestAlreadyExistsError(
                "An active removal request already exists for this superadmin"
            )

        total_superadmins = await self.membership_repo.count_superadmins(
            organization_id
        )
        if total_superadmins <= 1:
            raise CannotRemoveLastSuperadminError(
                "Cannot remove the only remaining superadmin"
            )

        required_votes = SuperadminQuorumService.calculate_required_votes(
            total_superadmins
        )

        now = datetime.now(timezone.utc)
        request = SuperadminRemovalRequest(
            id=uuid.uuid4(),
            organization_id=organization_id,
            target_user_id=target_user_id,
            requester_user_id=actor_user_id,
            reason=reason,
            status=RemovalRequestStatus.PENDING,
            required_votes=required_votes,
            created_at=now,
            updated_at=now,
            votes=[],
        )
        saved_request = await self.removal_repo.create_request(request)

        # Cast automatic approve vote for initiator
        initiator_vote = SuperadminRemovalVote(
            id=uuid.uuid4(),
            request_id=saved_request.id,
            voter_user_id=actor_user_id,
            decision=VoteDecision.APPROVE,
            voted_at=now,
        )
        await self.removal_repo.add_vote(initiator_vote)
        saved_request.votes.append(initiator_vote)

        new_status = SuperadminQuorumService.evaluate_status(
            saved_request, total_superadmins
        )
        if new_status != saved_request.status:
            await self.removal_repo.update_request_status(saved_request.id, new_status)
            saved_request.status = new_status
            if new_status == RemovalRequestStatus.APPROVED:
                target_membership.roles = [
                    r for r in target_membership.roles if r != OrgRole.SUPERADMIN
                ]
                await self.membership_repo.save(target_membership)
                await self.refresh_token_repo.revoke_all_for_user(target_user_id)

        return saved_request
