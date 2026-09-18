from datetime import datetime
from typing import Protocol
import uuid

from app.domain.entities.member_overall_score import MemberOverallScore


class MemberOverallScoreRepository(Protocol):
    async def save(
        self, member_overall_score: MemberOverallScore
    ) -> MemberOverallScore: ...

    async def get_latest_by_user_id(
        self, user_id: uuid.UUID
    ) -> MemberOverallScore | None: ...

    async def get_latest_by_user_ids(
        self, user_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, MemberOverallScore]: ...

    async def get_history_by_user_id(
        self, user_id: uuid.UUID
    ) -> list[MemberOverallScore]: ...

    async def get_history_by_organization_id(
        self, organization_id: uuid.UUID, since: datetime | None = None
    ) -> list[MemberOverallScore]: ...

    async def get_by_submission_id(
        self, submission_id: uuid.UUID
    ) -> MemberOverallScore | None: ...
