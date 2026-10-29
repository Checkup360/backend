import uuid
from collections.abc import Collection
from datetime import date
from typing import Protocol

from app.domain.entities import MemberDetails, Membership
from app.domain.repositories import (
    AssessmentSubmissionRepository,
    MemberDetailsRepository,
    MemberHealthDataRepository,
    OrganizationRepository,
    OrganizationScoreWeightsRepository,
)
from app.domain.services.form_completion import is_form_completed
from app.domain.services.form_registry import FormRegistry
from app.domain.services.member_health_topics import calculate_member_priority_topics
from app.domain.services.organization_form_policy import OrganizationFormPolicy
from app.domain.services.time_provider import TimeProvider
from app.domain.value_objects import OrgRole


class MemberUser(Protocol):
    @property
    def id(self) -> uuid.UUID: ...

    @property
    def is_superuser(self) -> bool: ...

    @property
    def membership(self) -> Membership | None: ...


class MemberDetailsService:
    def __init__(
        self,
        repo: MemberDetailsRepository,
        time_provider: TimeProvider,
        health_data_repo: MemberHealthDataRepository | None = None,
        submission_repo: AssessmentSubmissionRepository | None = None,
        form_registry: FormRegistry | None = None,
        score_weights_repo: OrganizationScoreWeightsRepository | None = None,
        org_repo: OrganizationRepository | None = None,
        form_policy: OrganizationFormPolicy | None = None,
    ):
        self.repo = repo
        self.time_provider = time_provider
        self.health_data_repo = health_data_repo
        self.submission_repo = submission_repo
        self.form_registry = form_registry
        self.score_weights_repo = score_weights_repo
        self.org_repo = org_repo
        self.form_policy = form_policy or OrganizationFormPolicy(
            form_registry=form_registry
        )

    def is_member_user(self, user: MemberUser) -> bool:
        if user.is_superuser:
            return False

        if user.membership is None:
            return False
        return OrgRole.MEMBER in user.membership.roles

    async def requires_onboarding(self, user: MemberUser) -> bool:
        if not self.is_member_user(user):
            return False
        return not await self.repo.exists_for_user(user.id)

    async def is_onboarded(self, user_id: uuid.UUID) -> bool:
        return await self.repo.exists_for_user(user_id)

    async def _score_weights_for_organization(
        self, organization_id: uuid.UUID
    ) -> dict[str, float] | None:
        if self.score_weights_repo:
            active_weights_rec = (
                await self.score_weights_repo.get_active_for_organization(
                    organization_id
                )
            )
            if active_weights_rec:
                return active_weights_rec.weights
        if self.org_repo:
            org = await self.org_repo.get(organization_id)
            if org:
                return org.score_weights
        return None

    async def get_required_forms_for_organization(
        self, organization_id: uuid.UUID
    ) -> list[str]:
        score_weights = await self._score_weights_for_organization(organization_id)
        return self.form_policy.get_active_form_types(score_weights=score_weights)

    async def get_required_form_fields_for_organization(
        self, organization_id: uuid.UUID
    ) -> dict[str, list[str]]:
        """Fields each required form asks the member, as the member sees them."""
        score_weights = await self._score_weights_for_organization(organization_id)
        definitions = self.form_policy.get_active_form_definitions(
            score_weights=score_weights
        )
        return {
            definition.form_type: list(definition.fields) for definition in definitions
        }

    async def _required_form_fields(
        self,
        required_forms: Collection[str] | None,
        organization_id: uuid.UUID | None,
    ) -> dict[str, list[str]]:
        if required_forms is None and organization_id is not None:
            return await self.get_required_form_fields_for_organization(organization_id)
        if self.form_registry is None:
            return {}
        if required_forms is None:
            required_forms = self.form_registry.get_registered_form_types()
        return {
            form_type: self.form_registry.get_form_fields(form_type)
            for form_type in required_forms
        }

    async def _completed_submission_form_types(self, user_id: uuid.UUID) -> set[str]:
        if self.submission_repo is None:
            return set()
        submissions, _ = await self.submission_repo.list_by_user(
            user_id, offset=0, limit=100
        )
        return {
            submission.form_type
            for submission in submissions
            if submission.status == "completed"
        }

    async def has_completed_all_forms(
        self,
        user_id: uuid.UUID,
        required_forms: Collection[str] | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> bool:
        required_fields = await self._required_form_fields(
            required_forms, organization_id
        )
        if not required_fields:
            return True

        completed_submissions = await self._completed_submission_form_types(user_id)
        health_data = None
        if self.health_data_repo is not None and any(
            form_type not in completed_submissions for form_type in required_fields
        ):
            health_data = await self.health_data_repo.get_by_user(user_id)

        return all(
            is_form_completed(
                fields,
                {name: getattr(health_data, name, None) for name in fields},
                has_completed_submission=form_type in completed_submissions,
            )
            for form_type, fields in required_fields.items()
        )

    async def get_profile(self, user_id: uuid.UUID) -> MemberDetails | None:
        return await self.repo.get_by_user(user_id)

    def get_priority_topics(self, details: MemberDetails | None) -> list[str]:
        return calculate_member_priority_topics(
            details, today=self.time_provider.today()
        )

    async def complete_onboarding(
        self,
        user: MemberUser,
        date_of_birth: date,
        phone_number: str | None = None,
        first_name: str = "",
        last_name: str = "",
        avatar_url: str | None = None,
    ) -> MemberDetails:
        if date_of_birth > self.time_provider.today():
            raise ValueError("date_of_birth_in_future")

        return await self.repo.save(
            MemberDetails(
                user_id=user.id,
                date_of_birth=date_of_birth,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                avatar_url=avatar_url,
            )
        )

    async def update_profile(
        self,
        user_id: uuid.UUID,
        first_name: str,
        last_name: str,
        phone_number: str | None,
        date_of_birth: date,
        avatar_url: str | None = None,
    ) -> MemberDetails:
        details = await self.repo.get_by_user(user_id)
        if details is None:
            raise ValueError("member_details_not_found")

        updated = MemberDetails(
            user_id=user_id,
            date_of_birth=date_of_birth,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            avatar_url=avatar_url,
        )
        return await self.repo.save(updated)
