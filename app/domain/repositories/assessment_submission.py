import uuid
from typing import Protocol

from app.domain.entities.assessment_submission import AssessmentSubmission


class AssessmentSubmissionRepository(Protocol):
    async def save(self, submission: AssessmentSubmission) -> AssessmentSubmission: ...

    async def update_status(self, submission_id: uuid.UUID, status: str) -> None: ...

    async def get_by_id(
        self, submission_id: uuid.UUID
    ) -> AssessmentSubmission | None: ...

    async def list_by_user(
        self, user_id: uuid.UUID, offset: int, limit: int
    ) -> tuple[list[AssessmentSubmission], int]: ...

    async def list_by_organization_employee(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        offset: int,
        limit: int,
    ) -> tuple[list[AssessmentSubmission], int]: ...
