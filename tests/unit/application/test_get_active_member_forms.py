import uuid
from unittest.mock import AsyncMock
import pytest

from app.domain.entities.organization import Organization
from app.application.use_cases.assessments.get_active_member_forms import (
    GetActiveMemberFormsUseCase,
)


@pytest.mark.asyncio
async def test_get_active_member_forms_returns_active_forms_for_org():
    org_id = uuid.uuid4()
    org_repo = AsyncMock()
    org_repo.get.return_value = Organization(
        id=org_id,
        name="Acme Corp",
        slug="acme",
        score_weights={"diabetes": 50.0, "depression": 0.0, "sleep_apnea": 0.0},
    )

    use_case = GetActiveMemberFormsUseCase(organization_repository=org_repo)
    active_forms = await use_case.execute(organization_id=org_id)

    form_types = [form.form_type for form in active_forms]
    assert "mood" not in form_types
    assert "sleep" not in form_types
    assert "biometrics" in form_types
    assert "habits" in form_types


@pytest.mark.asyncio
async def test_get_active_member_forms_without_org_id_returns_all_forms():
    org_repo = AsyncMock()
    use_case = GetActiveMemberFormsUseCase(organization_repository=org_repo)
    active_forms = await use_case.execute(organization_id=None)

    form_types = [form.form_type for form in active_forms]
    assert set(form_types) == {
        "biometrics",
        "sleep",
        "habits",
        "metabolic",
        "eoss",
        "mood",
    }
