from datetime import datetime, timezone
import uuid
import pytest
from unittest.mock import AsyncMock

from app.application.use_cases.organizations.recalculate_org_scores import (
    RecalculateOrganizationOverallScoresUseCase,
)
from app.domain.entities.organization_score_weights import OrganizationScoreWeights
from app.domain.entities.risk_score import RiskScore
from app.domain.entities.user import User
from app.domain.entities.employee import Employee
from app.domain.entities.organization import Organization


@pytest.fixture
def membership_repo():
    return AsyncMock()


@pytest.fixture
def risk_score_repo():
    return AsyncMock()


@pytest.fixture
def member_overall_score_repo():
    return AsyncMock()


@pytest.fixture
def score_weights_repo():
    return AsyncMock()


@pytest.fixture
def use_case(
    membership_repo, risk_score_repo, member_overall_score_repo, score_weights_repo
):
    return RecalculateOrganizationOverallScoresUseCase(
        membership_repo=membership_repo,
        risk_score_repo=risk_score_repo,
        member_overall_score_repo=member_overall_score_repo,
        score_weights_repo=score_weights_repo,
    )


@pytest.mark.asyncio
async def test_execute_recalculates_scores_for_all_members(
    use_case,
    membership_repo,
    risk_score_repo,
    member_overall_score_repo,
    score_weights_repo,
):
    # Arrange
    org_id = uuid.uuid4()
    user1_id = uuid.uuid4()
    user2_id = uuid.uuid4()

    # Mock active weights
    active_weights = OrganizationScoreWeights(
        id=uuid.uuid4(),
        organization_id=org_id,
        version=1,
        weights={"diabetes": 100.0, "sleep_apnea": 0.0},
        changed_by_user_id=None,
        created_at=datetime.now(timezone.utc),
    )
    score_weights_repo.get_active_for_organization.return_value = active_weights

    # Mock employees
    user1 = User(id=user1_id, email="u1@test.com")
    user2 = User(id=user2_id, email="u2@test.com")
    org = Organization(id=org_id, name="Test Org", slug="test-org")
    employee1 = Employee(user=user1, organization=org, roles=[])
    employee2 = Employee(user=user2, organization=org, roles=[])
    membership_repo.list_members_for_organization.return_value = [employee1, employee2]

    # Mock risk scores for users
    risk_score_1 = RiskScore(
        id=uuid.uuid4(),
        user_id=user1_id,
        score_name="diabetes",
        normalized_value=20.0,
        risk_level="Low",
        evaluated_at=datetime.now(timezone.utc),
        raw_value=20.0,
        explanation="",
        contributing_factors=[],
        attention_flags=[],
    )
    risk_score_2 = RiskScore(
        id=uuid.uuid4(),
        user_id=user2_id,
        score_name="diabetes",
        normalized_value=60.0,
        risk_level="High",
        evaluated_at=datetime.now(timezone.utc),
        raw_value=60.0,
        explanation="",
        contributing_factors=[],
        attention_flags=[],
    )

    # Return risk scores for user 1 and user 2
    async def mock_get_by_user_id(uid):
        if uid == user1_id:
            return [risk_score_1]
        elif uid == user2_id:
            return [risk_score_2]
        return []

    risk_score_repo.get_by_user_id.side_effect = mock_get_by_user_id

    # Act
    await use_case.execute(org_id)

    # Assert
    score_weights_repo.get_active_for_organization.assert_called_once_with(org_id)
    membership_repo.list_members_for_organization.assert_called_once_with(org_id)

    assert risk_score_repo.get_by_user_id.call_count == 2
    assert member_overall_score_repo.save.call_count == 2

    # Check the saved overall scores
    call_args_list = member_overall_score_repo.save.call_args_list

    saved_entity_1 = call_args_list[0][0][0]
    assert saved_entity_1.user_id == user1_id
    assert saved_entity_1.organization_id == org_id
    assert saved_entity_1.score_weights_id == active_weights.id
    assert saved_entity_1.overall_score == 20.0

    saved_entity_2 = call_args_list[1][0][0]
    assert saved_entity_2.user_id == user2_id
    assert saved_entity_2.organization_id == org_id
    assert saved_entity_2.score_weights_id == active_weights.id
    assert saved_entity_2.overall_score == 60.0


@pytest.mark.asyncio
async def test_execute_handles_no_active_weights(
    use_case,
    membership_repo,
    risk_score_repo,
    member_overall_score_repo,
    score_weights_repo,
):
    # Arrange
    org_id = uuid.uuid4()
    user1_id = uuid.uuid4()

    # Mock no active weights
    score_weights_repo.get_active_for_organization.return_value = None

    # Mock employees
    user1 = User(id=user1_id, email="u1@test.com")
    org = Organization(id=org_id, name="Test Org", slug="test-org")
    employee1 = Employee(user=user1, organization=org, roles=[])
    membership_repo.list_members_for_organization.return_value = [employee1]

    # Mock risk scores for users (must match DEFAULT_SCORE_WEIGHTS keys to not return None)
    risk_score_1 = RiskScore(
        id=uuid.uuid4(),
        user_id=user1_id,
        score_name="diabetes",
        normalized_value=50.0,
        risk_level="Medium",
        evaluated_at=datetime.now(timezone.utc),
        raw_value=50.0,
        explanation="",
        contributing_factors=[],
        attention_flags=[],
    )
    risk_score_2 = RiskScore(
        id=uuid.uuid4(),
        user_id=user1_id,
        score_name="sleep_apnea",
        normalized_value=50.0,
        risk_level="Medium",
        evaluated_at=datetime.now(timezone.utc),
        raw_value=50.0,
        explanation="",
        contributing_factors=[],
        attention_flags=[],
    )
    risk_score_3 = RiskScore(
        id=uuid.uuid4(),
        user_id=user1_id,
        score_name="depression",
        normalized_value=50.0,
        risk_level="Medium",
        evaluated_at=datetime.now(timezone.utc),
        raw_value=50.0,
        explanation="",
        contributing_factors=[],
        attention_flags=[],
    )
    risk_score_repo.get_by_user_id.return_value = [
        risk_score_1,
        risk_score_2,
        risk_score_3,
    ]

    # Act
    await use_case.execute(org_id)

    # Assert
    assert member_overall_score_repo.save.call_count == 1
    saved_entity = member_overall_score_repo.save.call_args[0][0]
    assert saved_entity.user_id == user1_id
    assert saved_entity.score_weights_id is None
    assert saved_entity.overall_score == 50.0
