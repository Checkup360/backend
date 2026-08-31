from datetime import date, datetime, timezone, timedelta
import uuid
import pytest
from pydantic import ValidationError

from app.domain.value_objects.org_role import OrgRole
from app.presentation.api.request_models.admin import (
    CreateSysadminInviteRequest,
    DeleteInvitesRequest as AdminDeleteInvitesRequest,
)
from app.presentation.api.request_models.invitations import (
    CreateOrganizationInviteRequest,
    DeleteInvitesRequest as OrgDeleteInvitesRequest,
)
from app.presentation.api.request_models.invite import RedeemInviteBody
from app.presentation.api.request_models.member_details import (
    MemberDetailsCreate,
    MemberProfileUpdate,
)
from app.presentation.api.request_models.organization import (
    CreateOrganizationRequest,
    DepartmentRequest,
    AssignDepartmentRequest,
)
from app.presentation.api.request_models.user import UserCreate
from app.presentation.api.response_models.admin import (
    CreateInviteResponse,
    SysadminInviteResponse,
    DeleteInvitesResponse,
)
from app.presentation.api.response_models.auth import (
    AuthMeResponse,
    OAuthAuthorizeResponse,
    OrganizationMembership,
)
from app.presentation.api.response_models.invitations import (
    OrganizationInviteResponse,
    InviteMetadataResponse,
    RedeemResponse,
)
from app.presentation.api.response_models.invite import (
    InviteRejected,
    PrepareGoogleSessionResponse,
)
from app.presentation.api.response_models.member_details import (
    MemberDetailsCreated,
    MemberProfileResponse,
)
from app.presentation.api.response_models.organization import (
    OrganizationResponse,
    OrganizationSummaryResponse,
    DepartmentResponse,
    OrganizationEmployeeResponse,
)
from app.presentation.api.response_models.user import UserRead


class TestRequestModelsValidation:
    def test_member_details_create_valid_phone(self):
        m = MemberDetailsCreate(
            date_of_birth=date(1990, 5, 20),
            first_name="Alice",
            last_name="Smith",
            phone_number="+54 11 1234 5678",
        )
        assert m.phone_number == "+54 11 1234 5678"

    def test_member_details_create_phone_stripping(self):
        m = MemberDetailsCreate(
            date_of_birth=date(1990, 5, 20),
            phone_number="  +54 11 1234 5678  ",
        )
        assert m.phone_number == "+54 11 1234 5678"

    def test_member_details_create_future_dob_raises(self):
        future = date.today() + timedelta(days=1)
        with pytest.raises(ValidationError):
            MemberDetailsCreate(
                date_of_birth=future,
                phone_number="+541112345678",
            )

    def test_member_details_create_invalid_phone_raises(self):
        with pytest.raises(ValidationError):
            MemberDetailsCreate(
                date_of_birth=date(1990, 1, 1),
                phone_number="not-a-phone",
            )

    def test_member_profile_update_validation(self):
        up = MemberProfileUpdate(
            first_name="Bob",
            last_name="Jones",
            phone_number="+1 (555) 000-1111",
            date_of_birth=date(1990, 5, 20),
        )
        assert up.first_name == "Bob"
        assert up.phone_number == "+1 (555) 000-1111"
        assert up.date_of_birth == date(1990, 5, 20)

        with pytest.raises(ValidationError):
            MemberProfileUpdate(
                first_name="Bob",
                last_name="Jones",
                phone_number="abc",
                date_of_birth=date(1990, 5, 20),
            )

    def test_create_organization_request(self):
        req = CreateOrganizationRequest(name="Alpha Org", slug="alpha-org")
        assert req.name == "Alpha Org"
        assert req.slug == "alpha-org"

    def test_admin_request_models(self):
        inv_req = CreateSysadminInviteRequest(
            email="admin@example.com", expires_in_hours=48
        )
        assert inv_req.email == "admin@example.com"
        assert inv_req.expires_in_hours == 48

        del_req = AdminDeleteInvitesRequest(ids=[uuid.uuid4()])
        assert len(del_req.ids) == 1

    def test_organization_invite_request_models(self):
        req = CreateOrganizationInviteRequest(
            email="user@example.com",
            role=OrgRole.MEMBER,
            organization_id=uuid.uuid4(),
        )
        assert req.role == OrgRole.MEMBER

        req_cm = CreateOrganizationInviteRequest(
            email="editor@example.com",
            role=OrgRole.CONTENT_MANAGER,
            organization_id=uuid.uuid4(),
        )
        assert req_cm.role == OrgRole.CONTENT_MANAGER

        del_req = OrgDeleteInvitesRequest(ids=[uuid.uuid4()])
        assert len(del_req.ids) == 1

    def test_redeem_invite_body(self):
        body = RedeemInviteBody(email="a@b.com", password="SecretPassword123!")
        assert body.email == "a@b.com"

    def test_department_request_models(self):
        dept_req = DepartmentRequest(name="Engineering")
        assert dept_req.name == "Engineering"

        assign_req = AssignDepartmentRequest(department_id=uuid.uuid4())
        assert assign_req.department_id is not None

    def test_user_create(self):
        uc = UserCreate(email="new@example.com", password="Password123!")
        assert uc.email == "new@example.com"


class TestResponseModelsSerialization:
    def test_admin_response_models(self):
        c_res = CreateInviteResponse(token="tok123", invite_url="http://x/tok123")
        assert c_res.token == "tok123"

        s_res = SysadminInviteResponse(
            id=uuid.uuid4(),
            token="tok123",
            email="a@b.com",
            max_uses=1,
            uses=0,
            expires_at=datetime.now(timezone.utc),
            invite_url="http://x",
        )
        assert s_res.token == "tok123"

        d_res = DeleteInvitesResponse(deleted_count=5)
        assert d_res.deleted_count == 5

    def test_auth_response_models(self):
        prep = PrepareGoogleSessionResponse(ok=True)
        assert prep.ok is True

        auth_me = AuthMeResponse(
            email="me@example.com",
            is_sysadmin=True,
            membership=OrganizationMembership(
                organization_id=uuid.uuid4(),
                organization_name="Org",
                roles=["admin"],
            ),
            requires_onboarding=False,
        )
        assert auth_me.email == "me@example.com"
        assert auth_me.is_sysadmin is True
        assert auth_me.membership.roles == ["admin"]

        oauth_resp = OAuthAuthorizeResponse(authorization_url="http://google.com")
        assert oauth_resp.authorization_url == "http://google.com"

    def test_invitation_response_models(self):
        meta = InviteMetadataResponse(
            organization_id=uuid.uuid4(),
            organization_name="Org",
            role="admin",
            is_sysadmin=False,
        )
        assert meta.organization_name == "Org"

        org_inv = OrganizationInviteResponse(
            id=uuid.uuid4(),
            token="tok",
            email="e@e.com",
            role="member",
            organization_id=uuid.uuid4(),
            organization_name="Org Name",
            department_id=None,
            department_name=None,
            max_uses=1,
            uses=0,
            expires_at=datetime.now(timezone.utc),
            invite_url="http://url",
        )
        assert org_inv.organization_name == "Org Name"

        red = RedeemResponse()
        assert red.ok is True

        rej = InviteRejected(code="expired")
        assert rej.code == "expired"

    def test_member_response_models(self):
        created = MemberDetailsCreated()
        assert created.ok is True

        prof = MemberProfileResponse(
            first_name="Jane",
            last_name="Doe",
            phone_number="+541112345678",
            date_of_birth=date(1995, 3, 15),
            avatar_url="data:image/png;base64,avatar123",
        )
        assert prof.first_name == "Jane"
        assert prof.avatar_url == "data:image/png;base64,avatar123"

    def test_organization_response_models(self):
        org_res = OrganizationResponse(
            id=uuid.uuid4(),
            name="Org",
            slug="org",
            collaborators_count=3,
        )
        assert org_res.collaborators_count == 3

        summary = OrganizationSummaryResponse(
            id=uuid.uuid4(),
            name="Org",
            slug="org",
            total_members=10,
            total_employees=8,
            total_admins=2,
        )
        assert summary.total_members == 10

        dept_res = DepartmentResponse(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            name="Dept",
            slug="dept",
        )
        assert dept_res.name == "Dept"

        emp_res = OrganizationEmployeeResponse(
            id=uuid.uuid4(),
            email="emp@example.com",
            roles=["member"],
            status="active",
            department=dept_res,
        )
        assert emp_res.email == "emp@example.com"

    def test_user_read_response_model(self):
        ur = UserRead(
            id=uuid.uuid4(),
            email="user@example.com",
            is_active=True,
            is_superuser=False,
            is_verified=True,
        )
        assert ur.email == "user@example.com"
