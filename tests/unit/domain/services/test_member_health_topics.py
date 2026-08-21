import uuid
from datetime import date

from app.domain.entities import MemberDetails
from app.domain.services.member_health_topics import (
    CMS_DISEASE_TOPICS,
    calculate_member_priority_topics,
)


def test_priority_topics_for_none_member():
    topics = calculate_member_priority_topics(None, today=date.today())
    assert topics == CMS_DISEASE_TOPICS


def test_priority_topics_for_senior_member():
    today = date.today()
    birth = date(today.year - 55, today.month, today.day)
    member = MemberDetails(
        user_id=uuid.uuid4(),
        date_of_birth=birth,
        first_name="Juan",
        last_name="Perez",
    )
    topics = calculate_member_priority_topics(member, today=today)
    assert topics[0] == "cardiovascular"
    assert topics[1] == "diabetes"
    assert "oncology" in topics
    assert len(topics) == len(CMS_DISEASE_TOPICS)


def test_priority_topics_for_young_member():
    today = date.today()
    birth = date(today.year - 25, today.month, today.day)
    member = MemberDetails(
        user_id=uuid.uuid4(),
        date_of_birth=birth,
        first_name="Ana",
        last_name="Gomez",
    )
    topics = calculate_member_priority_topics(member, today=today)
    assert topics[0] == "respiratory"
    assert topics[1] == "cardiovascular"
    assert len(topics) == len(CMS_DISEASE_TOPICS)


def test_priority_topics_with_custom_subset():
    member = MemberDetails(
        user_id=uuid.uuid4(),
        date_of_birth=date(1990, 1, 1),
    )
    subset = ["diabetes", "neurology"]
    topics = calculate_member_priority_topics(
        member, today=date.today(), available_topics=subset
    )
    assert set(topics) == set(subset)
