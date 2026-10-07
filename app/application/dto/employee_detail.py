from dataclasses import dataclass

from app.domain.entities import Employee, MemberDetails


@dataclass(frozen=True)
class EmployeeDetailDTO:
    employee: Employee
    profile: MemberDetails | None
    status: str | None
