import uuid
from datetime import date, datetime, timezone

from app.domain.entities import (
    Department,
    Employee,
    InviteToken,
    MemberDetails,
    Membership,
    Organization,
    User,
)
from app.domain.value_objects import OrgRole


def test_invite_token_is_exhausted_property():
    token = InviteToken(
        id=uuid.uuid4(),
        token="tok1",
        expires_at=datetime.now(timezone.utc),
        uses=0,
        max_uses=1,
    )
    assert token.is_exhausted is False

    token.uses = 1
    assert token.is_exhausted is True

    token.uses = 2
    assert token.is_exhausted is True


def test_department_dataclass_defaults():
    dept_id = uuid.uuid4()
    org_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    dept = Department(
        id=dept_id,
        organization_id=org_id,
        name="Engineering",
        slug="engineering",
        created_at=now,
        updated_at=now,
    )
    assert dept.id == dept_id
    assert dept.organization_id == org_id
    assert dept.name == "Engineering"
    assert dept.slug == "engineering"
    assert dept.created_at == now
    assert dept.updated_at == now


def test_employee_dataclass():
    user = User(id=uuid.uuid4(), email="emp@example.com")
    org = Organization(id=uuid.uuid4(), name="Acme", slug="acme")
    dept = Department(
        id=uuid.uuid4(), organization_id=org.id, name="Sales", slug="sales"
    )

    employee = Employee(
        user=user,
        organization=org,
        roles=[OrgRole.MEMBER],
        department=dept,
    )

    assert employee.user == user
    assert employee.organization == org
    assert employee.roles == [OrgRole.MEMBER]
    assert employee.department == dept


def test_member_details_dataclass():
    user_id = uuid.uuid4()
    dob = date(1995, 8, 20)
    details = MemberDetails(user_id=user_id, date_of_birth=dob)
    assert details.user_id == user_id
    assert details.date_of_birth == dob


def test_membership_dataclass_defaults():
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    membership = Membership(
        user_id=user_id,
        organization_id=org_id,
        roles=[OrgRole.ADMIN, OrgRole.MEMBER],
    )
    assert membership.user_id == user_id
    assert membership.organization_id == org_id
    assert membership.roles == [OrgRole.ADMIN, OrgRole.MEMBER]
    assert membership.department_id is None


def test_organization_dataclass_defaults():
    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Health Corp", slug="health-corp")
    assert org.id == org_id
    assert org.name == "Health Corp"
    assert org.slug == "health-corp"
    assert org.collaborators_count == 0


def test_user_dataclass_defaults():
    user_id = uuid.uuid4()
    user = User(id=user_id, email="test@example.com")
    assert user.id == user_id
    assert user.email == "test@example.com"
    assert user.is_superuser is False
    assert user.is_active is True


def test_member_biometrics_dataclass():
    from app.domain.entities.member_biometrics import MemberBiometrics

    user_id = uuid.uuid4()
    bio = MemberBiometrics(
        user_id=user_id,
        biological_sex="M",
        height=1.75,
        weight=80.0,
        waist_circumference=90.0,
        neck_circumference=40.0,
        snoring=True,
        tired=False,
        observed_apnea=False,
        hypertension_medication=True,
        daily_physical_activity=True,
        fruits_vegetables=True,
        previous_high_glucose=False,
        family_diabetes="first_degree",
    )
    assert bio.user_id == user_id
    assert bio.biological_sex == "M"
    assert bio.height == 1.75
    assert bio.weight == 80.0
    assert bio.waist_circumference == 90.0
    assert bio.neck_circumference == 40.0
    assert bio.snoring is True
    assert bio.tired is False
    assert bio.observed_apnea is False
    assert bio.hypertension_medication is True
    assert bio.daily_physical_activity is True
    assert bio.fruits_vegetables is True
    assert bio.previous_high_glucose is False
    assert bio.family_diabetes == "first_degree"
