import re
import unicodedata
import uuid

from app.domain.entities.department import Department
from app.domain.exceptions import (
    DepartmentInUseError,
    DepartmentNotFoundError,
    DepartmentSlugAlreadyExists,
)
from app.domain.services.membership import MembershipService
from app.persistence.repositories.department import DepartmentRepository
from app.persistence.repositories.membership import MembershipRepository


def build_department_slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.strip())
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    if not slug:
        raise ValueError("invalid_department_name")
    return slug


class DepartmentService:
    def __init__(
        self,
        department_repo: DepartmentRepository,
        membership_service: MembershipService,
        membership_repo: MembershipRepository,
    ):
        self.department_repo = department_repo
        self.membership_service = membership_service
        self.membership_repo = membership_repo

    async def list_departments(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> list[Department]:
        await self.membership_service.get_admin_membership(user_id, organization_id)
        return await self.department_repo.list_by_organization(organization_id)

    async def list_departments_as_superuser(
        self, organization_id: uuid.UUID
    ) -> list[Department]:
        return await self.department_repo.list_by_organization(organization_id)

    async def create_department(
        self, user_id: uuid.UUID, organization_id: uuid.UUID, name: str
    ) -> Department:
        await self.membership_service.get_admin_membership(user_id, organization_id)
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("department_name_required")
        slug = build_department_slug(clean_name)
        existing = await self.department_repo.get_by_organization_and_slug(
            organization_id, slug
        )
        if existing:
            raise DepartmentSlugAlreadyExists()
        return await self.department_repo.create(
            id=uuid.uuid4(),
            organization_id=organization_id,
            name=clean_name,
            slug=slug,
        )

    async def update_department(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        department_id: uuid.UUID,
        name: str,
    ) -> Department:
        await self.membership_service.get_admin_membership(user_id, organization_id)
        department = await self.department_repo.get_by_organization(
            organization_id, department_id
        )
        if not department:
            raise DepartmentNotFoundError()
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("department_name_required")
        slug = build_department_slug(clean_name)
        existing = await self.department_repo.get_by_organization_and_slug(
            organization_id, slug
        )
        if existing and existing.id != department_id:
            raise DepartmentSlugAlreadyExists()
        updated = await self.department_repo.update(
            department_id, name=clean_name, slug=slug
        )
        if not updated:
            raise DepartmentNotFoundError()
        return updated

    async def delete_department(
        self, user_id: uuid.UUID, organization_id: uuid.UUID, department_id: uuid.UUID
    ) -> None:
        await self.membership_service.get_admin_membership(user_id, organization_id)
        department = await self.department_repo.get_by_organization(
            organization_id, department_id
        )
        if not department:
            raise DepartmentNotFoundError()
        if await self.department_repo.count_memberships(department_id):
            raise DepartmentInUseError()
        await self.department_repo.delete_by_organization(
            organization_id, department_id
        )

    async def assign_employee_department(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        employee_user_id: uuid.UUID,
        department_id: uuid.UUID | None,
    ):
        await self.membership_service.get_admin_membership(user_id, organization_id)
        if department_id is not None:
            department = await self.department_repo.get_by_organization(
                organization_id, department_id
            )
            if not department:
                raise DepartmentNotFoundError()

        membership = await self.membership_repo.get_by_user_and_org(
            employee_user_id, organization_id
        )
        if not membership:
            raise DepartmentNotFoundError()
        membership.department_id = department_id
        await self.membership_repo.save(membership)
        employee = await self.membership_repo.get_employee(
            employee_user_id, organization_id
        )
        if not employee:
            raise DepartmentNotFoundError()
        return employee
