import uuid
from typing import Protocol

from app.domain.entities.employee_summary import EmployeeSummary
from app.domain.value_objects.employee_directory_query import EmployeeDirectoryQuery


class EmployeeDirectoryRepository(Protocol):
    async def search(
        self, organization_id: uuid.UUID, query: EmployeeDirectoryQuery
    ) -> tuple[list[EmployeeSummary], int]:
        """Return the requested page and the total of matching employees."""
        ...
