from datetime import datetime, timezone
import uuid

from app.domain.entities import Organization, OrganizationScoreWeights
from app.domain.exceptions import (
    OrganizationNotFoundError,
    OrganizationSlugAlreadyExists,
)
from app.domain.repositories import OrganizationRepository
from app.domain.repositories.organization_score_weights import (
    OrganizationScoreWeightsRepository,
)
from app.domain.services.health_index_classification import DEFAULT_RISK_THRESHOLDS
from app.domain.services.risk_score_calculator import DEFAULT_SCORE_WEIGHTS


class OrganizationService:
    def __init__(
        self,
        repo: OrganizationRepository,
        score_weights_repo: OrganizationScoreWeightsRepository | None = None,
    ):
        self.repo = repo
        self.score_weights_repo = score_weights_repo

    async def create_organization(self, name: str, slug: str) -> Organization:
        existing = await self.repo.get_by_slug(slug)
        if existing:
            raise OrganizationSlugAlreadyExists()

        org = await self.repo.create(name=name, slug=slug)

        if self.score_weights_repo:
            initial_weights = OrganizationScoreWeights(
                id=uuid.uuid4(),
                organization_id=org.id,
                version=1,
                weights=dict(DEFAULT_SCORE_WEIGHTS),
                risk_thresholds=dict(DEFAULT_RISK_THRESHOLDS),
                changed_by_user_id=None,
                created_at=datetime.now(timezone.utc),
            )
            await self.score_weights_repo.save(initial_weights)

        return org

    async def list_organizations(self) -> list[Organization]:
        return await self.repo.list()

    async def search_organizations(
        self,
        status: str | None = None,
        search: str | None = None,
        page: int | None = None,
        page_size: int = 10,
    ) -> tuple[list[Organization], int]:
        return await self.repo.search(
            status=status, search=search, page=page, page_size=page_size
        )

    async def get_organization(self, id: uuid.UUID) -> Organization | None:
        return await self.repo.get(id)

    async def delete_organization(self, id: uuid.UUID) -> bool:
        return await self.repo.delete(id)

    async def get_score_weights(self, id: uuid.UUID) -> dict[str, float]:
        weights, _ = await self.get_score_weights_and_thresholds(id)
        return weights

    async def get_score_weights_and_thresholds(
        self, id: uuid.UUID
    ) -> tuple[dict[str, float], dict[str, float]]:
        if self.score_weights_repo:
            active = await self.score_weights_repo.get_active_for_organization(id)
            if active and active.weights:
                thresholds = (
                    active.risk_thresholds
                    if active.risk_thresholds
                    else dict(DEFAULT_RISK_THRESHOLDS)
                )
                return active.weights, thresholds

        org = await self.repo.get(id)
        if not org:
            raise OrganizationNotFoundError()
        weights = (
            org.score_weights if org.score_weights else dict(DEFAULT_SCORE_WEIGHTS)
        )
        thresholds = (
            org.risk_thresholds
            if org.risk_thresholds
            else dict(DEFAULT_RISK_THRESHOLDS)
        )
        return weights, thresholds

    async def update_score_weights(
        self,
        id: uuid.UUID,
        score_weights: dict[str, float],
        risk_thresholds: dict[str, float] | None = None,
        changed_by_user_id: uuid.UUID | None = None,
    ) -> Organization:
        org = await self.repo.get(id)
        if not org:
            raise OrganizationNotFoundError()
        for k, v in score_weights.items():
            if not isinstance(v, (int, float)) or v < 0:
                raise ValueError(f"Invalid weight value for '{k}'")

        if risk_thresholds is not None:
            if "low" not in risk_thresholds or "moderate" not in risk_thresholds:
                raise ValueError("risk_thresholds_must_contain_low_and_moderate")
            low_val = float(risk_thresholds["low"])
            mod_val = float(risk_thresholds["moderate"])
            if not (0.0 <= mod_val < low_val <= 100.0):
                raise ValueError("invalid_risk_threshold_ranges")

        updated = await self.repo.update_score_weights(
            id, score_weights, risk_thresholds=risk_thresholds
        )
        if not updated:
            raise OrganizationNotFoundError()

        if self.score_weights_repo:
            latest = await self.score_weights_repo.get_active_for_organization(id)
            next_version = (latest.version + 1) if latest else 1
            effective_thresholds = (
                risk_thresholds
                if risk_thresholds is not None
                else (
                    latest.risk_thresholds if latest else dict(DEFAULT_RISK_THRESHOLDS)
                )
            )
            weights_entry = OrganizationScoreWeights(
                id=uuid.uuid4(),
                organization_id=id,
                version=next_version,
                weights=score_weights,
                risk_thresholds=effective_thresholds,
                changed_by_user_id=changed_by_user_id,
                created_at=datetime.now(timezone.utc),
            )
            await self.score_weights_repo.save(weights_entry)

        return updated

    async def update_organization_name(self, id: uuid.UUID, name: str) -> Organization:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("organization_name_empty")
        org = await self.repo.get(id)
        if not org:
            raise OrganizationNotFoundError()
        updated = await self.repo.update(id, name=cleaned_name)
        if not updated:
            raise OrganizationNotFoundError()
        return updated
