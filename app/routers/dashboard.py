import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.machinery.users import current_active_user
from app.dependencies import get_membership_service
from app.domain.exceptions import NotOrganizationAdminError
from app.domain.services.membership import MembershipService
from app.persistence.models import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardEmployeeResponse(BaseModel):
    id: uuid.UUID
    email: str
    roles: list[str]


class DashboardSummaryResponse(BaseModel):
    total_employees: int


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: User = Depends(current_active_user),
    membership_service: MembershipService = Depends(get_membership_service),
):
    try:
        total_employees = await membership_service.count_employees_for_admin(
            current_user.id
        )
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )

    return DashboardSummaryResponse(total_employees=total_employees)


@router.get("/employees", response_model=list[DashboardEmployeeResponse])
async def list_dashboard_employees(
    current_user: User = Depends(current_active_user),
    membership_service: MembershipService = Depends(get_membership_service),
):
    try:
        employees = await membership_service.list_employees_for_admin(current_user.id)
    except NotOrganizationAdminError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )

    return [
        DashboardEmployeeResponse(
            id=employee.user.id,
            email=employee.user.email,
            roles=[r.value for r in employee.roles],
        )
        for employee in employees
    ]
