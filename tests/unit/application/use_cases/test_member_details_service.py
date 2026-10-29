import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.use_cases.members.member_details_service import (
    MemberDetailsService,
)
from app.domain.entities import MemberDetails
from app.domain.value_objects.org_role import OrgRole
from app.domain.services.time_provider import TimeProvider


_FROZEN_TODAY = date(2025, 6, 15)


class FrozenTimeProvider(TimeProvider):
    def utcnow(self) -> datetime:
        return datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    def today(self) -> date:
        return _FROZEN_TODAY


def make_user(*, is_superuser=False, roles=None, has_membership=True):
    membership = None
    if has_membership:
        if roles is not None:
            membership = SimpleNamespace(roles=roles)
        elif not is_superuser:
            membership = SimpleNamespace(roles=[OrgRole.MEMBER])

    return SimpleNamespace(
        id=uuid.uuid4(),
        is_superuser=is_superuser,
        membership=membership,
    )


def test_is_member_user_returns_false_when_membership_is_none():
    user = make_user(has_membership=False)
    service = MemberDetailsService(AsyncMock(), FrozenTimeProvider())
    assert service.is_member_user(user) is False


@pytest.mark.asyncio
async def test_requires_onboarding_for_member_user_without_details():
    repo = AsyncMock()
    repo.exists_for_user.return_value = False

    users = [
        make_user(roles=[OrgRole.MEMBER]),
        make_user(roles=[OrgRole.MEMBER, OrgRole.ADMIN]),
    ]

    service = MemberDetailsService(repo, FrozenTimeProvider())

    for user in users:
        assert await service.requires_onboarding(user) is True
        repo.exists_for_user.assert_awaited_with(user.id)


@pytest.mark.asyncio
async def test_does_not_require_onboarding_for_member_with_details():
    repo = AsyncMock()
    repo.exists_for_user.return_value = True
    user = make_user(roles=[OrgRole.MEMBER])

    service = MemberDetailsService(repo, FrozenTimeProvider())

    assert await service.requires_onboarding(user) is False


@pytest.mark.asyncio
async def test_does_not_require_onboarding_for_sysadmin_or_non_member():
    repo = AsyncMock()
    service = MemberDetailsService(repo, FrozenTimeProvider())

    users = [
        make_user(is_superuser=True, roles=[OrgRole.MEMBER]),
        make_user(roles=[OrgRole.ADMIN]),
        make_user(roles=[]),
    ]

    for user in users:
        assert await service.requires_onboarding(user) is False

    repo.exists_for_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_is_onboarded_returns_false_if_no_details():
    repo = AsyncMock()
    repo.exists_for_user.return_value = False
    user_id = uuid.uuid4()

    service = MemberDetailsService(repo, FrozenTimeProvider())
    result = await service.is_onboarded(user_id)

    assert result is False
    repo.exists_for_user.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_is_onboarded_delegates_to_repo():
    repo = AsyncMock()
    repo.exists_for_user.return_value = True
    user_id = uuid.uuid4()

    service = MemberDetailsService(repo, FrozenTimeProvider())
    result = await service.is_onboarded(user_id)

    assert result is True
    repo.exists_for_user.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_has_completed_all_forms_returns_false_when_forms_incomplete():
    from app.domain.services.form_registry import FormDefinition, FormRegistry

    repo = AsyncMock()
    repo.exists_for_user.return_value = True
    user_id = uuid.uuid4()

    submission_repo = AsyncMock()
    # User has completed biometrics, but sleep and habits are missing
    submission_repo.list_by_user.return_value = (
        [SimpleNamespace(form_type="biometrics", status="completed")],
        1,
    )

    health_data_repo = AsyncMock()
    health_data_repo.get_by_user.return_value = None

    form_registry = FormRegistry(
        forms=[
            FormDefinition(form_type="biometrics", fields=["height"]),
            FormDefinition(form_type="sleep", fields=["snoring"]),
        ]
    )

    service = MemberDetailsService(
        repo,
        FrozenTimeProvider(),
        health_data_repo=health_data_repo,
        submission_repo=submission_repo,
        form_registry=form_registry,
    )
    result = await service.has_completed_all_forms(user_id)

    assert result is False


@pytest.mark.asyncio
async def test_has_completed_all_forms_returns_true_when_all_forms_completed():
    from app.domain.services.form_registry import FormDefinition, FormRegistry

    repo = AsyncMock()
    repo.exists_for_user.return_value = True
    user_id = uuid.uuid4()

    submission_repo = AsyncMock()
    submission_repo.list_by_user.return_value = (
        [
            SimpleNamespace(form_type="biometrics", status="completed"),
            SimpleNamespace(form_type="sleep", status="completed"),
        ],
        2,
    )

    health_data_repo = AsyncMock()

    form_registry = FormRegistry(
        forms=[
            FormDefinition(form_type="biometrics", fields=["height"]),
            FormDefinition(form_type="sleep", fields=["snoring"]),
        ]
    )

    service = MemberDetailsService(
        repo,
        FrozenTimeProvider(),
        health_data_repo=health_data_repo,
        submission_repo=submission_repo,
        form_registry=form_registry,
    )
    result = await service.has_completed_all_forms(user_id)

    assert result is True


@pytest.mark.asyncio
async def test_has_completed_all_forms_dynamically_requires_new_forms():
    from app.domain.services.form_registry import FormDefinition, FormRegistry

    repo = AsyncMock()
    repo.exists_for_user.return_value = True
    user_id = uuid.uuid4()

    submission_repo = AsyncMock()
    submission_repo.list_by_user.return_value = (
        [
            SimpleNamespace(form_type="biometrics", status="completed"),
            SimpleNamespace(form_type="sleep", status="completed"),
        ],
        2,
    )

    # A new form "cardiovascular" is added to FormRegistry
    form_registry = FormRegistry(
        forms=[
            FormDefinition(form_type="biometrics", fields=["height"]),
            FormDefinition(form_type="sleep", fields=["snoring"]),
            FormDefinition(form_type="cardiovascular", fields=["systolic_bp"]),
        ]
    )

    health_data_repo = AsyncMock()
    health_data_repo.get_by_user.return_value = None

    service = MemberDetailsService(
        repo,
        FrozenTimeProvider(),
        health_data_repo=health_data_repo,
        submission_repo=submission_repo,
        form_registry=form_registry,
    )

    # Should return False because "cardiovascular" is not completed
    assert await service.has_completed_all_forms(user_id) is False


@pytest.mark.asyncio
async def test_has_completed_all_forms_ignores_fields_shared_with_another_form():
    from types import SimpleNamespace as Row

    from app.domain.services.form_registry import FormDefinition, FormRegistry

    repo = AsyncMock()
    submission_repo = AsyncMock()
    submission_repo.list_by_user.return_value = ([], 0)
    # Only the neck circumference, which biometrics and sleep share
    health_data_repo = AsyncMock()
    health_data_repo.get_by_user.return_value = Row(
        height=170.0, neck_circumference=38.0, snoring=None, tired=None
    )
    form_registry = FormRegistry(
        forms=[
            FormDefinition(
                form_type="biometrics", fields=["height", "neck_circumference"]
            ),
            FormDefinition(
                form_type="sleep",
                fields=["snoring", "tired", "neck_circumference"],
            ),
        ]
    )
    service = MemberDetailsService(
        repo,
        FrozenTimeProvider(),
        health_data_repo=health_data_repo,
        submission_repo=submission_repo,
        form_registry=form_registry,
    )

    assert await service.has_completed_all_forms(uuid.uuid4()) is False


@pytest.mark.asyncio
async def test_has_completed_all_forms_is_true_when_every_field_has_a_value():
    from types import SimpleNamespace as Row

    from app.domain.services.form_registry import FormDefinition, FormRegistry

    repo = AsyncMock()
    submission_repo = AsyncMock()
    submission_repo.list_by_user.return_value = ([], 0)
    health_data_repo = AsyncMock()
    health_data_repo.get_by_user.return_value = Row(
        height=170.0, neck_circumference=38.0, snoring=False, tired=True
    )
    form_registry = FormRegistry(
        forms=[
            FormDefinition(
                form_type="biometrics", fields=["height", "neck_circumference"]
            ),
            FormDefinition(
                form_type="sleep",
                fields=["snoring", "tired", "neck_circumference"],
            ),
        ]
    )
    service = MemberDetailsService(
        repo,
        FrozenTimeProvider(),
        health_data_repo=health_data_repo,
        submission_repo=submission_repo,
        form_registry=form_registry,
    )

    assert await service.has_completed_all_forms(uuid.uuid4()) is True


@pytest.mark.asyncio
async def test_complete_onboarding_success():
    repo = AsyncMock()
    user = make_user()
    dob = date(1990, 5, 15)
    phone = "+541112345678"
    expected_details = MemberDetails(
        user_id=user.id, date_of_birth=dob, phone_number=phone
    )
    repo.save.return_value = expected_details

    service = MemberDetailsService(repo, FrozenTimeProvider())
    result = await service.complete_onboarding(user, dob, phone_number=phone)

    assert result == expected_details
    repo.save.assert_awaited_once_with(
        MemberDetails(user_id=user.id, date_of_birth=dob, phone_number=phone)
    )


@pytest.mark.asyncio
async def test_complete_onboarding_rejects_future_date():
    repo = AsyncMock()
    service = MemberDetailsService(repo, FrozenTimeProvider())

    with pytest.raises(ValueError, match="date_of_birth_in_future"):
        await service.complete_onboarding(
            make_user(),
            date.today() + timedelta(days=1),
            phone_number="+541112345678",
        )

    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_profile_success_and_not_found():
    repo = AsyncMock()
    user_id = uuid.uuid4()
    existing = MemberDetails(
        user_id=user_id,
        date_of_birth=date(1992, 1, 1),
        first_name="OldFirst",
        last_name="OldLast",
    )
    repo.get_by_user.return_value = existing
    repo.save.side_effect = lambda details: details

    service = MemberDetailsService(repo, FrozenTimeProvider())
    updated = await service.update_profile(
        user_id=user_id,
        first_name="NewFirst",
        last_name="NewLast",
        phone_number="+541199998888",
        date_of_birth=date(1995, 2, 2),
        avatar_url="data:image/png;base64,newphoto",
    )

    assert updated.first_name == "NewFirst"
    assert updated.last_name == "NewLast"
    assert updated.phone_number == "+541199998888"
    assert updated.date_of_birth == date(1995, 2, 2)
    assert updated.avatar_url == "data:image/png;base64,newphoto"

    removed_avatar = await service.update_profile(
        user_id=user_id,
        first_name="NewFirst",
        last_name="NewLast",
        phone_number="+541199998888",
        date_of_birth=date(1995, 2, 2),
        avatar_url=None,
    )
    assert removed_avatar.avatar_url is None

    repo.get_by_user.return_value = None
    with pytest.raises(ValueError, match="member_details_not_found"):
        await service.update_profile(
            user_id=user_id,
            first_name="NewFirst",
            last_name="NewLast",
            phone_number=None,
            date_of_birth=date(1995, 2, 2),
        )


@pytest.mark.asyncio
async def test_has_completed_all_forms_with_required_forms_subset():
    from app.domain.services.form_registry import FormDefinition, FormRegistry

    user_id = uuid.uuid4()
    submission_repo = AsyncMock()
    # Member only submitted biometrics and habits (which are the required ones)
    submission_repo.list_by_user.return_value = (
        [
            SimpleNamespace(form_type="biometrics", status="completed"),
            SimpleNamespace(form_type="habits", status="completed"),
        ],
        2,
    )

    form_registry = FormRegistry(
        forms=[
            FormDefinition(form_type="biometrics", fields=["height"]),
            FormDefinition(form_type="habits", fields=["smoker"]),
            FormDefinition(form_type="sleep", fields=["snoring"]),
            FormDefinition(form_type="mood", fields=["phq9_q1"]),
        ]
    )

    service = MemberDetailsService(
        AsyncMock(),
        FrozenTimeProvider(),
        submission_repo=submission_repo,
        form_registry=form_registry,
    )

    # When specifying required_forms as only the subset, it should return True
    assert (
        await service.has_completed_all_forms(
            user_id, required_forms=["biometrics", "habits"]
        )
        is True
    )

    # But if required_forms includes sleep as well, it should return False
    assert (
        await service.has_completed_all_forms(
            user_id, required_forms=["biometrics", "habits", "sleep"]
        )
        is False
    )


@pytest.mark.asyncio
async def test_has_completed_all_forms_resolves_organization_id():
    from app.domain.services.form_registry import FormDefinition, FormRegistry

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    submission_repo = AsyncMock()
    submission_repo.list_by_user.return_value = (
        [
            SimpleNamespace(form_type="biometrics", status="completed"),
            SimpleNamespace(form_type="habits", status="completed"),
        ],
        2,
    )

    score_weights_repo = AsyncMock()
    # Only diabetes score is enabled (> 0)
    score_weights_repo.get_active_for_organization.return_value = SimpleNamespace(
        weights={"diabetes": 1.0, "sleep_apnea": 0.0, "depression": 0.0}
    )

    form_registry = FormRegistry(
        forms=[
            FormDefinition(form_type="biometrics", fields=["height"]),
            FormDefinition(form_type="habits", fields=["smoker"]),
            FormDefinition(form_type="sleep", fields=["snoring"]),
        ]
    )

    service = MemberDetailsService(
        AsyncMock(),
        FrozenTimeProvider(),
        submission_repo=submission_repo,
        form_registry=form_registry,
        score_weights_repo=score_weights_repo,
    )

    # Organization only requires biometrics and habits for diabetes
    assert (
        await service.has_completed_all_forms(user_id, organization_id=org_id) is True
    )
