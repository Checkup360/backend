import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.use_cases.departments import DepartmentService
from app.domain.entities.department import Department
from app.domain.exceptions import (
    DepartmentInUseError,
    DepartmentNotFoundError,
    DepartmentSlugAlreadyExists,
)
from app.domain.services.department_policy import build_department_slug


def test_build_department_slug_normalizes_name():
    assert build_department_slug("  People Operations  ") == "people-operations"


# --- List Departments Tests ---


@pytest.mark.asyncio
async def test_list_departments_verifies_admin_and_returns_list():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    mock_depts = [MagicMock(spec=Department), MagicMock(spec=Department)]
    department_repo.list_by_organization.return_value = mock_depts

    service = DepartmentService(department_repo, membership_service, membership_repo)
    result = await service.list_departments(user_id, org_id)

    assert result == mock_depts
    membership_service.get_admin_membership.assert_awaited_once_with(user_id, org_id)
    department_repo.list_by_organization.assert_awaited_once_with(org_id)


@pytest.mark.asyncio
async def test_list_departments_as_superuser_bypasses_admin_check():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    org_id = uuid.uuid4()
    mock_depts = [MagicMock(spec=Department)]
    department_repo.list_by_organization.return_value = mock_depts

    service = DepartmentService(department_repo, membership_service, membership_repo)
    result = await service.list_departments_as_superuser(org_id)

    assert result == mock_depts
    membership_service.get_admin_membership.assert_not_awaited()
    department_repo.list_by_organization.assert_awaited_once_with(org_id)


# --- Create Department Tests ---


@pytest.mark.asyncio
async def test_create_department_normalizes_slug_and_checks_admin():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    user_id = uuid.uuid4()
    organization_id = uuid.uuid4()
    created = Department(
        id=uuid.uuid4(),
        organization_id=organization_id,
        name="People Operations",
        slug="people-operations",
    )
    department_repo.get_by_organization_and_slug.return_value = None
    department_repo.create.return_value = created

    service = DepartmentService(department_repo, membership_service, membership_repo)
    result = await service.create_department(
        user_id, organization_id, "People Operations"
    )

    assert result == created
    membership_service.get_admin_membership.assert_awaited_once_with(
        user_id, organization_id
    )
    department_repo.create.assert_awaited_once()
    assert department_repo.create.call_args.kwargs["slug"] == "people-operations"


@pytest.mark.asyncio
async def test_create_department_empty_name_raises_value_error():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    service = DepartmentService(department_repo, membership_service, membership_repo)

    with pytest.raises(ValueError, match="department_name_required"):
        await service.create_department(uuid.uuid4(), uuid.uuid4(), "   ")


@pytest.mark.asyncio
async def test_create_department_rejects_duplicate_slug():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    organization_id = uuid.uuid4()
    department_repo.get_by_organization_and_slug.return_value = MagicMock()

    service = DepartmentService(department_repo, membership_service, membership_repo)

    with pytest.raises(DepartmentSlugAlreadyExists):
        await service.create_department(uuid.uuid4(), organization_id, "People")


# --- Update Department Tests ---


@pytest.mark.asyncio
async def test_update_department_success():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    dept_id = uuid.uuid4()
    existing_dept = MagicMock(id=dept_id, name="Old Name", slug="old-name")
    updated_dept = MagicMock(id=dept_id, name="New Name", slug="new-name")

    department_repo.get_by_organization.return_value = existing_dept
    department_repo.get_by_organization_and_slug.return_value = None
    department_repo.update.return_value = updated_dept

    service = DepartmentService(department_repo, membership_service, membership_repo)
    result = await service.update_department(user_id, org_id, dept_id, "New Name")

    assert result == updated_dept
    membership_service.get_admin_membership.assert_awaited_once_with(user_id, org_id)
    department_repo.get_by_organization.assert_awaited_once_with(org_id, dept_id)
    department_repo.update.assert_awaited_once_with(
        dept_id, name="New Name", slug="new-name"
    )


@pytest.mark.asyncio
async def test_update_department_same_slug_success():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    dept_id = uuid.uuid4()
    existing_dept = MagicMock(id=dept_id, name="Name", slug="name")

    department_repo.get_by_organization.return_value = existing_dept
    # Same department returned for slug check
    department_repo.get_by_organization_and_slug.return_value = existing_dept
    department_repo.update.return_value = existing_dept

    service = DepartmentService(department_repo, membership_service, membership_repo)
    result = await service.update_department(user_id, org_id, dept_id, "Name")

    assert result == existing_dept


@pytest.mark.asyncio
async def test_update_department_not_found_raises_error():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    department_repo.get_by_organization.return_value = None

    service = DepartmentService(department_repo, membership_service, membership_repo)

    with pytest.raises(DepartmentNotFoundError):
        await service.update_department(
            uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "New Name"
        )


@pytest.mark.asyncio
async def test_update_department_empty_name_raises_value_error():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    dept_id = uuid.uuid4()
    department_repo.get_by_organization.return_value = MagicMock(id=dept_id)

    service = DepartmentService(department_repo, membership_service, membership_repo)

    with pytest.raises(ValueError, match="department_name_required"):
        await service.update_department(uuid.uuid4(), uuid.uuid4(), dept_id, "  ")


@pytest.mark.asyncio
async def test_update_department_duplicate_slug_other_id_raises_error():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    dept_id = uuid.uuid4()
    other_dept_id = uuid.uuid4()

    department_repo.get_by_organization.return_value = MagicMock(id=dept_id)
    department_repo.get_by_organization_and_slug.return_value = MagicMock(
        id=other_dept_id
    )

    service = DepartmentService(department_repo, membership_service, membership_repo)

    with pytest.raises(DepartmentSlugAlreadyExists):
        await service.update_department(
            uuid.uuid4(), uuid.uuid4(), dept_id, "Other Name"
        )


@pytest.mark.asyncio
async def test_update_department_repo_returns_none_raises_not_found():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    dept_id = uuid.uuid4()

    department_repo.get_by_organization.return_value = MagicMock(id=dept_id)
    department_repo.get_by_organization_and_slug.return_value = None
    department_repo.update.return_value = None

    service = DepartmentService(department_repo, membership_service, membership_repo)

    with pytest.raises(DepartmentNotFoundError):
        await service.update_department(uuid.uuid4(), uuid.uuid4(), dept_id, "New Name")


# --- Delete Department Tests ---


@pytest.mark.asyncio
async def test_delete_department_success():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    dept_id = uuid.uuid4()

    department_repo.get_by_organization.return_value = MagicMock(id=dept_id)
    department_repo.count_memberships.return_value = 0

    service = DepartmentService(department_repo, membership_service, membership_repo)
    await service.delete_department(user_id, org_id, dept_id)

    membership_service.get_admin_membership.assert_awaited_once_with(user_id, org_id)
    department_repo.delete_by_organization.assert_awaited_once_with(org_id, dept_id)


@pytest.mark.asyncio
async def test_delete_department_not_found_raises_error():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    department_repo.get_by_organization.return_value = None

    service = DepartmentService(department_repo, membership_service, membership_repo)

    with pytest.raises(DepartmentNotFoundError):
        await service.delete_department(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_delete_department_in_use_raises_error():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    dept_id = uuid.uuid4()

    department_repo.get_by_organization.return_value = MagicMock(id=dept_id)
    department_repo.count_memberships.return_value = 3

    service = DepartmentService(department_repo, membership_service, membership_repo)

    with pytest.raises(DepartmentInUseError):
        await service.delete_department(uuid.uuid4(), uuid.uuid4(), dept_id)

    department_repo.delete_by_organization.assert_not_awaited()


# --- Assign Employee Department Tests ---


@pytest.mark.asyncio
async def test_assign_employee_department_success():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    admin_user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    emp_user_id = uuid.uuid4()
    dept_id = uuid.uuid4()

    dept = MagicMock(id=dept_id)
    membership = MagicMock()
    employee = MagicMock()

    department_repo.get_by_organization.return_value = dept
    membership_repo.get_by_user_and_org.return_value = membership
    membership_repo.get_employee.return_value = employee

    service = DepartmentService(department_repo, membership_service, membership_repo)
    result = await service.assign_employee_department(
        admin_user_id, org_id, emp_user_id, dept_id
    )

    assert result == employee
    assert membership.department_id == dept_id
    membership_repo.save.assert_awaited_once_with(membership)
    membership_repo.get_employee.assert_awaited_once_with(emp_user_id, org_id)


@pytest.mark.asyncio
async def test_assign_employee_department_unassign_success():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    admin_user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    emp_user_id = uuid.uuid4()

    membership = MagicMock()
    employee = MagicMock()

    membership_repo.get_by_user_and_org.return_value = membership
    membership_repo.get_employee.return_value = employee

    service = DepartmentService(department_repo, membership_service, membership_repo)
    result = await service.assign_employee_department(
        admin_user_id, org_id, emp_user_id, None
    )

    assert result == employee
    assert membership.department_id is None
    department_repo.get_by_organization.assert_not_awaited()
    membership_repo.save.assert_awaited_once_with(membership)


@pytest.mark.asyncio
async def test_assign_employee_department_invalid_dept_raises_error():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    department_repo.get_by_organization.return_value = None

    service = DepartmentService(department_repo, membership_service, membership_repo)

    with pytest.raises(DepartmentNotFoundError):
        await service.assign_employee_department(
            uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        )


@pytest.mark.asyncio
async def test_assign_employee_department_membership_not_found_raises_error():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    dept_id = uuid.uuid4()

    department_repo.get_by_organization.return_value = MagicMock(id=dept_id)
    membership_repo.get_by_user_and_org.return_value = None

    service = DepartmentService(department_repo, membership_service, membership_repo)

    with pytest.raises(DepartmentNotFoundError):
        await service.assign_employee_department(
            uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), dept_id
        )


@pytest.mark.asyncio
async def test_assign_employee_department_employee_not_found_raises_error():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()
    dept_id = uuid.uuid4()

    department_repo.get_by_organization.return_value = MagicMock(id=dept_id)
    membership_repo.get_by_user_and_org.return_value = MagicMock()
    membership_repo.get_employee.return_value = None

    service = DepartmentService(department_repo, membership_service, membership_repo)

    with pytest.raises(DepartmentNotFoundError):
        await service.assign_employee_department(
            uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), dept_id
        )


@pytest.mark.asyncio
async def test_assign_employee_department_reassigns_from_dept1_to_dept2():
    department_repo = AsyncMock()
    membership_service = AsyncMock()
    membership_repo = AsyncMock()

    admin_user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    emp_user_id = uuid.uuid4()

    dept1_id = uuid.uuid4()
    dept2_id = uuid.uuid4()

    dept2 = MagicMock(id=dept2_id, name="Sales")
    # Employee was initially in dept1
    membership = MagicMock(department_id=dept1_id)
    updated_employee = MagicMock(department_id=dept2_id)

    department_repo.get_by_organization.return_value = dept2
    membership_repo.get_by_user_and_org.return_value = membership
    membership_repo.get_employee.return_value = updated_employee

    service = DepartmentService(department_repo, membership_service, membership_repo)
    result = await service.assign_employee_department(
        admin_user_id, org_id, emp_user_id, dept2_id
    )

    assert result == updated_employee
    assert membership.department_id == dept2_id
    membership_repo.save.assert_awaited_once_with(membership)
