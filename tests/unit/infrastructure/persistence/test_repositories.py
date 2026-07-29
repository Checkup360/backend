import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.entities import (
    Department,
    InviteToken,
    MemberDetails,
    Membership,
    Organization,
)
from app.domain.value_objects import OrgRole
from app.infrastructure.persistence.models import (
    Department as DepartmentORM,
    InviteToken as InviteTokenORM,
    MemberDetails as MemberDetailsORM,
    Membership as MembershipORM,
    Organization as OrganizationORM,
    User as UserORM,
)
from app.infrastructure.persistence.repositories.base import BaseRepository
from app.infrastructure.persistence.repositories.department import DepartmentRepository
from app.infrastructure.persistence.repositories.invite import (
    InviteRepository,
    _department_from_orm,
    _organization_from_orm,
)
from app.infrastructure.persistence.repositories.member_details import (
    MemberDetailsRepository,
)
from app.infrastructure.persistence.repositories.membership import MembershipRepository
from app.infrastructure.persistence.repositories.organization import (
    OrganizationRepository,
)
from app.infrastructure.persistence.repositories.user import UserRepository


# --- BaseRepository Tests ---


@pytest.mark.asyncio
async def test_base_repository_methods(mock_db_session):
    repo = BaseRepository(OrganizationORM, mock_db_session)

    # _from_domain type check
    with pytest.raises(TypeError, match="Domain entities must be dataclasses"):
        repo._from_domain("not_a_dataclass")

    # get found vs missing
    org_id = uuid.uuid4()
    mock_db_session.get.return_value = None
    assert await repo.get(org_id) is None

    # list
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_db_session.scalars.return_value = mock_scalars
    repo._to_domain = MagicMock(return_value="domain_obj")
    assert await repo.list() == []

    # create
    repo._to_domain = MagicMock(return_value="created_domain")
    res = await repo.create(name="Org")
    assert res == "created_domain"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_awaited()

    # update existing vs missing
    mock_db_session.get.return_value = None
    assert await repo.update(org_id, name="New") is None

    orm_instance = SimpleNamespace(name="Old")
    mock_db_session.get.return_value = orm_instance
    repo._to_domain = MagicMock(return_value="updated_domain")
    assert await repo.update(org_id, name="New") == "updated_domain"
    assert orm_instance.name == "New"

    # save existing vs new
    mock_db_session.get.return_value = orm_instance
    repo._from_domain = MagicMock(return_value={"id": org_id, "name": "Saved"})
    assert (
        await repo.save(Organization(id=org_id, name="Saved", slug="saved"))
        == "updated_domain"
    )

    mock_db_session.get.return_value = None
    assert (
        await repo.save(Organization(id=org_id, name="Saved", slug="saved"))
        == "updated_domain"
    )

    # delete
    result_mock = MagicMock()
    result_mock.rowcount = 1
    mock_db_session.execute.return_value = result_mock
    assert await repo.delete(org_id) is True

    result_mock.rowcount = 0
    assert await repo.delete(org_id) is False


# --- UserRepository Tests ---


@pytest.mark.asyncio
async def test_user_repository(mock_db_session):
    repo = UserRepository(mock_db_session)
    user_id = uuid.uuid4()
    user_orm = UserORM(
        id=user_id, email="u@example.com", is_superuser=False, is_active=True
    )

    domain_user = repo._to_domain(user_orm)
    assert domain_user.id == user_id
    assert domain_user.email == "u@example.com"

    d = repo._from_domain(domain_user)
    assert d["email"] == "u@example.com"


# --- DepartmentRepository Tests ---


@pytest.mark.asyncio
async def test_department_repository(mock_db_session):
    repo = DepartmentRepository(mock_db_session)
    org_id = uuid.uuid4()
    dept_id = uuid.uuid4()

    dept_orm = DepartmentORM(
        id=dept_id,
        organization_id=org_id,
        name="Eng",
        slug="eng",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # list_by_organization
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [dept_orm]
    mock_db_session.scalars.return_value = mock_scalars
    depts = await repo.list_by_organization(org_id)
    assert len(depts) == 1
    assert depts[0].name == "Eng"

    # get_by_organization found & missing
    mock_db_session.scalar.return_value = dept_orm
    assert (await repo.get_by_organization(org_id, dept_id)).name == "Eng"

    mock_db_session.scalar.return_value = None
    assert await repo.get_by_organization(org_id, dept_id) is None

    # get_by_organization_and_slug found & missing
    mock_db_session.scalar.return_value = dept_orm
    assert (await repo.get_by_organization_and_slug(org_id, "eng")).name == "Eng"

    mock_db_session.scalar.return_value = None
    assert await repo.get_by_organization_and_slug(org_id, "eng") is None

    # count_memberships
    mock_db_session.scalar.return_value = 5
    assert await repo.count_memberships(dept_id) == 5

    mock_db_session.scalar.return_value = None
    assert await repo.count_memberships(dept_id) == 0

    # delete_by_organization
    res_mock = MagicMock()
    res_mock.rowcount = 1
    mock_db_session.execute.return_value = res_mock
    assert await repo.delete_by_organization(org_id, dept_id) is True

    # _from_domain
    d = repo._from_domain(
        Department(id=dept_id, organization_id=org_id, name="Eng", slug="eng")
    )
    assert d["slug"] == "eng"


# --- MemberDetailsRepository Tests ---


@pytest.mark.asyncio
async def test_member_details_repository(mock_db_session):
    repo = MemberDetailsRepository(mock_db_session)
    user_id = uuid.uuid4()
    dt = datetime.now(timezone.utc).date()

    details = MemberDetails(user_id=user_id, date_of_birth=dt)
    orm = MemberDetailsORM(user_id=user_id, date_of_birth=dt)

    # save existing
    mock_db_session.get.return_value = orm
    updated = await repo.save(details)
    assert updated.user_id == user_id

    # save new
    mock_db_session.get.return_value = None
    repo.create = AsyncMock(return_value=details)
    created = await repo.save(details)
    assert created.user_id == user_id

    # exists_for_user
    mock_db_session.get.return_value = orm
    assert await repo.exists_for_user(user_id) is True

    mock_db_session.get.return_value = None
    assert await repo.exists_for_user(user_id) is False


# --- OrganizationRepository Tests ---


@pytest.mark.asyncio
async def test_organization_repository(mock_db_session):
    repo = OrganizationRepository(mock_db_session)
    org_id = uuid.uuid4()
    org_orm = OrganizationORM(id=org_id, name="Acme", slug="acme")

    # get found & missing
    row_mock = MagicMock()
    row_mock.first.return_value = (org_orm, 3)
    mock_db_session.execute.return_value = row_mock

    fetched = await repo.get(org_id)
    assert fetched is not None
    assert fetched.collaborators_count == 3

    row_mock.first.return_value = None
    assert await repo.get(org_id) is None

    # get_by_slug found & missing
    row_mock.first.return_value = (org_orm, 2)
    by_slug = await repo.get_by_slug("acme")
    assert by_slug.collaborators_count == 2

    row_mock.first.return_value = None
    assert await repo.get_by_slug("acme") is None

    # list
    result_mock = MagicMock()
    result_mock.all.return_value = [(org_orm, 4)]
    mock_db_session.execute.return_value = result_mock
    orgs = await repo.list()
    assert len(orgs) == 1
    assert orgs[0].collaborators_count == 4

    # delete
    execute_mock = MagicMock()
    execute_mock.rowcount = 1
    mock_db_session.execute.return_value = execute_mock
    assert await repo.delete(org_id) is True

    # _to_domain & _from_domain
    dom = repo._to_domain(org_orm)
    assert dom.name == "Acme"
    assert repo._from_domain(dom)["slug"] == "acme"


# --- MembershipRepository Tests ---


@pytest.mark.asyncio
async def test_membership_repository(mock_db_session):
    repo = MembershipRepository(mock_db_session)
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    dept_id = uuid.uuid4()

    user_orm = UserORM(
        id=user_id, email="u@example.com", is_superuser=False, is_active=True
    )
    org_orm = OrganizationORM(id=org_id, name="Acme", slug="acme")
    dept_orm = DepartmentORM(
        id=dept_id,
        organization_id=org_id,
        name="Eng",
        slug="eng",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mem_orm = MembershipORM(
        user_id=user_id,
        organization_id=org_id,
        roles=["admin"],
        department_id=dept_id,
        user=user_orm,
        organization=org_orm,
        department=dept_orm,
    )

    # get_by_user_and_org found & missing
    execute_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.first.return_value = mem_orm
    execute_mock.scalars.return_value = scalars_mock
    mock_db_session.execute.return_value = execute_mock

    assert (await repo.get_by_user_and_org(user_id, org_id)).roles == [OrgRole.ADMIN]

    scalars_mock.first.return_value = None
    assert await repo.get_by_user_and_org(user_id, org_id) is None

    # is_admin_of_any
    result_mock = MagicMock()
    result_mock.first.return_value = mem_orm
    mock_db_session.execute.return_value = result_mock
    assert await repo.is_admin_of_any(user_id) is True

    result_mock.first.return_value = None
    assert await repo.is_admin_of_any(user_id) is False

    # get_admin_organization_id
    mock_db_session.scalar.return_value = org_id
    assert await repo.get_admin_organization_id(user_id) == org_id

    # list_members_for_organization (with roles and without department)
    mem_orm_no_dept = MembershipORM(
        user_id=user_id,
        organization_id=org_id,
        roles=["member"],
        department_id=None,
        user=user_orm,
        organization=org_orm,
        department=None,
    )
    scalars_res = MagicMock()
    scalars_res.unique.return_value.all.return_value = [mem_orm, mem_orm_no_dept]
    mock_db_session.scalars.return_value = scalars_res

    employees = await repo.list_members_for_organization(org_id, roles=[OrgRole.ADMIN])
    assert len(employees) == 2
    assert employees[0].department is not None
    assert employees[1].department is None

    # get_employee found & missing
    mock_db_session.scalar.return_value = mem_orm
    emp = await repo.get_employee(user_id, org_id)
    assert emp is not None
    assert emp.user.id == user_id

    mock_db_session.scalar.return_value = None
    assert await repo.get_employee(user_id, org_id) is None

    # count_members_for_organization
    mock_db_session.scalar.return_value = 10
    assert (
        await repo.count_members_for_organization(org_id, roles=[OrgRole.MEMBER]) == 10
    )

    mock_db_session.scalar.return_value = None
    assert await repo.count_members_for_organization(org_id) == 0

    # save existing & new
    save_execute_mock = MagicMock()
    save_execute_mock.scalars.return_value.first.return_value = mem_orm
    mock_db_session.execute.return_value = save_execute_mock

    saved = await repo.save(
        Membership(user_id=user_id, organization_id=org_id, roles=[OrgRole.ADMIN])
    )
    assert saved.user_id == user_id

    save_execute_mock.scalars.return_value.first.return_value = None
    repo.create = AsyncMock(
        return_value=Membership(
            user_id=user_id, organization_id=org_id, roles=[OrgRole.ADMIN]
        )
    )
    assert (
        await repo.save(
            Membership(user_id=user_id, organization_id=org_id, roles=[OrgRole.ADMIN])
        )
    ).user_id == user_id


# --- InviteRepository Tests ---


@pytest.mark.asyncio
async def test_invite_repository(mock_db_session):
    repo = InviteRepository(mock_db_session)
    invite_id = uuid.uuid4()
    org_id = uuid.uuid4()
    dept_id = uuid.uuid4()

    invite_orm = InviteTokenORM(
        id=invite_id,
        token="tok123",
        email="test@example.com",
        max_uses=1,
        uses=0,
        expires_at=datetime.now(timezone.utc),
        organization_id=org_id,
        department_id=dept_id,
        role="admin",
        is_sysadmin=False,
    )
    invite_orm.organization = None
    invite_orm.department = None

    # Helper functions
    assert _organization_from_orm(invite_orm) is None
    assert _department_from_orm(invite_orm) is None

    # get found & missing
    mock_db_session.scalar.return_value = invite_orm
    fetched = await repo.get(invite_id)
    assert fetched is not None
    assert fetched.token == "tok123"

    mock_db_session.scalar.return_value = None
    assert await repo.get(invite_id) is None

    # get_by_token found & missing
    mock_db_session.scalar.return_value = invite_orm
    assert (await repo.get_by_token("tok123")).token == "tok123"

    mock_db_session.scalar.return_value = None
    assert await repo.get_by_token("tok123") is None

    # list_filtered for all status options ("used", "expired", "active", None)
    mock_db_session.scalar.return_value = 1
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [invite_orm]
    mock_db_session.scalars.return_value = mock_scalars

    for status_val in ["used", "expired", "active", None]:
        invites, count = await repo.list_filtered(
            organization_id=org_id,
            is_sysadmin=False,
            role=OrgRole.ADMIN,
            status=status_val,
            page=1,
            page_size=10,
        )
        assert count == 1
        assert len(invites) == 1

    # delete_filtered
    res_mock = MagicMock()
    res_mock.rowcount = 2
    mock_db_session.execute.return_value = res_mock
    del_count = await repo.delete_filtered(
        ids=[invite_id],
        is_sysadmin=False,
        organization_id=org_id,
    )
    assert del_count == 2

    # _from_domain
    dom = InviteToken(
        id=invite_id,
        token="tok123",
        email="test@example.com",
        max_uses=1,
        uses=0,
        expires_at=datetime.now(timezone.utc),
    )
    assert repo._from_domain(dom)["token"] == "tok123"
