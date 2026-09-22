from app.domain.entities.superadmin_removal import (
    RemovalRequestStatus,
    SuperadminRemovalRequest,
    VoteDecision,
)
from app.domain.exceptions import CannotRemoveLastSuperadminError


class SuperadminQuorumService:
    @staticmethod
    def calculate_required_votes(total_superadmins: int) -> int:
        if total_superadmins <= 1:
            raise CannotRemoveLastSuperadminError("cannot_remove_last_superadmin")
        return (total_superadmins // 2) + 1

    @staticmethod
    def evaluate_status(
        request: SuperadminRemovalRequest,
        total_superadmins: int,
    ) -> RemovalRequestStatus:
        approves = sum(1 for v in request.votes if v.decision == VoteDecision.APPROVE)
        rejects = sum(1 for v in request.votes if v.decision == VoteDecision.REJECT)

        if approves >= request.required_votes:
            return RemovalRequestStatus.APPROVED

        # Target superadmin cannot vote on their own removal,
        # so eligible voters count is total_superadmins - 1
        total_eligible_voters = max(0, total_superadmins - 1)
        max_possible_approves = total_eligible_voters - rejects
        if max_possible_approves < request.required_votes:
            return RemovalRequestStatus.REJECTED

        return RemovalRequestStatus.PENDING
