import uuid
from datetime import datetime, timezone

from app.infrastructure.persistence import database
from app.infrastructure.persistence.models import (
    Department,
    InviteToken,
    MemberDetails,
    Membership,
    OAuthAccount,
    Organization,
    User,
)


def test_database_module():
    assert database.Base is not None
    assert database.engine is not None
    assert database.async_session_maker is not None


def test_models_instantiation():
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hash",
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    assert user.email == "test@example.com"

    oauth_acc = OAuthAccount(
        id=uuid.uuid4(),
        user_id=user.id,
        oauth_name="google",
        access_token="tok",
        account_id="acc123",
        account_email="google@example.com",
    )
    assert oauth_acc.oauth_name == "google"

    org = Organization(id=uuid.uuid4(), name="Acme", slug="acme")
    assert org.name == "Acme"

    dept = Department(
        id=uuid.uuid4(), organization_id=org.id, name="Sales", slug="sales"
    )
    assert dept.name == "Sales"

    details = MemberDetails(
        user_id=user.id, date_of_birth=datetime.now(timezone.utc).date()
    )
    assert details.user_id == user.id

    membership = Membership(user_id=user.id, organization_id=org.id, roles=["admin"])
    assert membership.roles == ["admin"]

    invite = InviteToken(
        id=uuid.uuid4(),
        token="tok",
        expires_at=datetime.now(timezone.utc),
        email="user@example.com",
    )
    assert invite.token == "tok"
