from datetime import datetime, timezone
import uuid

from app.domain.entities.member_overall_score import MemberOverallScore
from app.domain.entities.organization_score_weights import OrganizationScoreWeights


def test_member_overall_score_entity_instantiation():
    score_id = uuid.uuid4()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    weights_id = uuid.uuid4()
    sub_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    entity = MemberOverallScore(
        id=score_id,
        user_id=user_id,
        organization_id=org_id,
        score_weights_id=weights_id,
        submission_id=sub_id,
        overall_score=42.5,
        risk_level="Moderate risk",
        evaluated_at=now,
    )

    assert entity.id == score_id
    assert entity.user_id == user_id
    assert entity.organization_id == org_id
    assert entity.score_weights_id == weights_id
    assert entity.submission_id == sub_id
    assert entity.overall_score == 42.5
    assert entity.risk_level == "Moderate risk"
    assert entity.evaluated_at == now


def test_organization_score_weights_entity_instantiation():
    weights_id = uuid.uuid4()
    org_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    weights = {"cardiovascular": 40.0, "depression": 60.0}

    entity = OrganizationScoreWeights(
        id=weights_id,
        organization_id=org_id,
        version=2,
        weights=weights,
        changed_by_user_id=admin_id,
        created_at=now,
    )

    assert entity.id == weights_id
    assert entity.organization_id == org_id
    assert entity.version == 2
    assert entity.weights == weights
    assert entity.changed_by_user_id == admin_id
    assert entity.created_at == now


def test_organization_score_weights_initial_creation_without_user():
    weights_id = uuid.uuid4()
    org_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    weights = {"cardiovascular": 25.0, "diabetes": 20.0}

    entity = OrganizationScoreWeights(
        id=weights_id,
        organization_id=org_id,
        version=1,
        weights=weights,
        changed_by_user_id=None,
        created_at=now,
    )

    assert entity.id == weights_id
    assert entity.organization_id == org_id
    assert entity.version == 1
    assert entity.changed_by_user_id is None
