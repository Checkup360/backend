from datetime import datetime, timezone
import uuid
import pytest

from app.domain.entities.superadmin_removal import (
    RemovalRequestStatus,
    SuperadminRemovalRequest,
    SuperadminRemovalVote,
    VoteDecision,
)
from app.domain.exceptions import CannotRemoveLastSuperadminError
from app.domain.services.superadmin_quorum import SuperadminQuorumService


def _make_request(
    required_votes: int,
    votes: list[SuperadminRemovalVote] | None = None,
) -> SuperadminRemovalRequest:
    return SuperadminRemovalRequest(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        target_user_id=uuid.uuid4(),
        requester_user_id=uuid.uuid4(),
        status=RemovalRequestStatus.PENDING,
        required_votes=required_votes,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        votes=votes or [],
    )


def _make_vote(
    request_id: uuid.UUID,
    decision: VoteDecision,
) -> SuperadminRemovalVote:
    return SuperadminRemovalVote(
        id=uuid.uuid4(),
        request_id=request_id,
        voter_user_id=uuid.uuid4(),
        decision=decision,
        voted_at=datetime.now(timezone.utc),
    )


class TestSuperadminQuorumService:
    def test_calculate_required_votes_disallows_single_or_zero_superadmin(self):
        with pytest.raises(CannotRemoveLastSuperadminError):
            SuperadminQuorumService.calculate_required_votes(1)

        with pytest.raises(CannotRemoveLastSuperadminError):
            SuperadminQuorumService.calculate_required_votes(0)

    @pytest.mark.parametrize(
        ("total_superadmins", "expected_required"),
        [
            (2, 2),
            (3, 2),
            (4, 3),
            (5, 3),
            (6, 4),
            (7, 4),
        ],
    )
    def test_calculate_required_votes_values(
        self, total_superadmins: int, expected_required: int
    ):
        assert (
            SuperadminQuorumService.calculate_required_votes(total_superadmins)
            == expected_required
        )

    def test_evaluate_status_pending_when_votes_insufficient(self):
        req = _make_request(required_votes=2)
        req.votes.append(_make_vote(req.id, VoteDecision.APPROVE))

        status = SuperadminQuorumService.evaluate_status(req, total_superadmins=3)
        assert status == RemovalRequestStatus.PENDING

    def test_evaluate_status_approved_when_quorum_reached(self):
        req = _make_request(required_votes=2)
        req.votes.append(_make_vote(req.id, VoteDecision.APPROVE))
        req.votes.append(_make_vote(req.id, VoteDecision.APPROVE))

        status = SuperadminQuorumService.evaluate_status(req, total_superadmins=3)
        assert status == RemovalRequestStatus.APPROVED

    def test_evaluate_status_rejected_when_impossible_to_reach_quorum(self):
        # 3 superadmins (total_eligible=2), required=2. If 1 other eligible rejects, max possible approves is 1 < 2 -> REJECTED
        req = _make_request(required_votes=2)
        req.votes.append(_make_vote(req.id, VoteDecision.APPROVE))
        req.votes.append(_make_vote(req.id, VoteDecision.REJECT))

        status = SuperadminQuorumService.evaluate_status(req, total_superadmins=3)
        assert status == RemovalRequestStatus.REJECTED
