from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class RemovalRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class VoteDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


@dataclass
class SuperadminRemovalVote:
    id: uuid.UUID
    request_id: uuid.UUID
    voter_user_id: uuid.UUID
    decision: VoteDecision
    voted_at: datetime


@dataclass
class SuperadminRemovalRequest:
    id: uuid.UUID
    organization_id: uuid.UUID
    target_user_id: uuid.UUID
    requester_user_id: uuid.UUID
    status: RemovalRequestStatus
    required_votes: int
    created_at: datetime
    updated_at: datetime
    reason: str | None = None
    votes: list[SuperadminRemovalVote] = field(default_factory=list)
