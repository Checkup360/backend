from datetime import date, datetime
from typing import Any
import uuid
import pytest

from app.application.use_cases.audit.get_organization_audit_logs import (
    GetOrganizationAuditLogsUseCase,
)
from app.application.use_cases.audit.get_organization_compliance_summary import (
    GetOrganizationComplianceSummaryUseCase,
)
from app.domain.entities.audit_log import AuditLog
from app.domain.entities.member_details import MemberDetails
from app.domain.entities.membership import Membership, OrgRole
from app.domain.entities.organization import Organization
from app.domain.entities.user import User
from app.domain.exceptions import OrganizationNotFoundError
from app.domain.repositories.audit_log import AuditLogRepository
from app.domain.repositories.member_details import MemberDetailsRepository
from app.domain.repositories.membership import MembershipRepository
from app.domain.repositories.organization import OrganizationRepository
from app.domain.repositories.user import UserRepository


class InMemoryAuditLogRepository(AuditLogRepository):
    def __init__(self) -> None:
        self.logs: list[AuditLog] = []

    async def log(self, audit_log: AuditLog) -> AuditLog:
        self.logs.append(audit_log)
        return audit_log

    async def get_by_user_id(
        self, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[AuditLog]:
        filtered = [entry for entry in self.logs if entry.user_id == user_id]
        return filtered[offset : offset + limit]

    async def get_by_organization_id(
        self, organization_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[AuditLog]:
        filtered = [
            entry for entry in self.logs if entry.organization_id == organization_id
        ]
        return filtered[offset : offset + limit]

    async def list_by_organization(
        self,
        organization_id: uuid.UUID,
        action: str | None = None,
        user_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        filtered = [
            entry for entry in self.logs if entry.organization_id == organization_id
        ]
        if action:
            filtered = [entry for entry in filtered if entry.action == action]
        if user_id:
            filtered = [entry for entry in filtered if entry.user_id == user_id]
        if from_date:
            filtered = [entry for entry in filtered if entry.created_at >= from_date]
        if to_date:
            filtered = [entry for entry in filtered if entry.created_at <= to_date]
        return filtered[offset : offset + limit], len(filtered)

    async def list_all(
        self,
        action: str | None = None,
        organization_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        filtered = self.logs
        if organization_id:
            filtered = [
                entry for entry in filtered if entry.organization_id == organization_id
            ]
        if action:
            filtered = [entry for entry in filtered if entry.action == action]
        if user_id:
            filtered = [entry for entry in filtered if entry.user_id == user_id]
        if from_date:
            filtered = [entry for entry in filtered if entry.created_at >= from_date]
        if to_date:
            filtered = [entry for entry in filtered if entry.created_at <= to_date]
        return filtered[offset : offset + limit], len(filtered)

    async def get_compliance_stats(self, organization_id: uuid.UUID) -> dict[str, Any]:
        org_logs = [
            entry for entry in self.logs if entry.organization_id == organization_id
        ]
        accepted = sum(1 for entry in org_logs if entry.action == "CONSENT_ACCEPTED")
        revoked = sum(1 for entry in org_logs if entry.action == "CONSENT_REVOKED")
        exported = sum(1 for entry in org_logs if entry.action == "DATA_EXPORTED")
        users = len({entry.user_id for entry in org_logs if entry.user_id is not None})
        return {
            "total_audit_events": len(org_logs),
            "consent_accepted_count": accepted,
            "consent_revoked_count": revoked,
            "data_exported_count": exported,
            "audited_members_count": users,
            "actions_breakdown": {
                "CONSENT_ACCEPTED": accepted,
                "CONSENT_REVOKED": revoked,
                "DATA_EXPORTED": exported,
            },
        }


class InMemoryOrgRepo(OrganizationRepository):
    def __init__(self) -> None:
        self.orgs: dict[uuid.UUID, Organization] = {}

    async def get(self, org_id: uuid.UUID) -> Organization | None:
        return self.orgs.get(org_id)

    async def get_by_name(self, name: str) -> Organization | None:
        return next((o for o in self.orgs.values() if o.name == name), None)

    async def save(self, organization: Organization) -> Organization:
        self.orgs[organization.id] = organization
        return organization

    async def list_all(self, offset: int = 0, limit: int = 50) -> list[Organization]:
        return list(self.orgs.values())[offset : offset + limit]

    async def delete(self, org_id: uuid.UUID) -> bool:
        return bool(self.orgs.pop(org_id, None))


class InMemoryUserRepo(UserRepository):
    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}

    async def get(self, user_id: uuid.UUID) -> User | None:
        return self.users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users.values() if u.email == email), None)

    async def save(self, user: User) -> User:
        self.users[user.id] = user
        return user


class InMemoryMemberDetailsRepo(MemberDetailsRepository):
    def __init__(self) -> None:
        self.details: dict[uuid.UUID, MemberDetails] = {}

    async def get_by_user(self, user_id: uuid.UUID) -> MemberDetails | None:
        return self.details.get(user_id)

    async def save(self, member_details: MemberDetails) -> MemberDetails:
        self.details[member_details.user_id] = member_details
        return member_details


class InMemoryMembershipRepo(MembershipRepository):
    def __init__(self) -> None:
        self.memberships: list[Membership] = []

    async def count_members_for_organization(
        self, organization_id: uuid.UUID, roles: list[OrgRole] | None = None
    ) -> int:
        return len(
            [m for m in self.memberships if m.organization_id == organization_id]
        )

    async def list_by_organization(self, org_id: uuid.UUID) -> list[Membership]:
        return [m for m in self.memberships if m.organization_id == org_id]

    async def get_by_user(self, user_id: uuid.UUID) -> Membership | None:
        return next((m for m in self.memberships if m.user_id == user_id), None)

    async def get_by_user_and_org(
        self, user_id: uuid.UUID, org_id: uuid.UUID
    ) -> Membership | None:
        return next(
            (
                m
                for m in self.memberships
                if m.user_id == user_id and m.organization_id == org_id
            ),
            None,
        )

    async def save(self, membership: Membership) -> Membership:
        self.memberships.append(membership)
        return membership

    async def delete(self, user_id: uuid.UUID, org_id: uuid.UUID) -> bool:
        self.memberships = [
            m
            for m in self.memberships
            if not (m.user_id == user_id and m.organization_id == org_id)
        ]
        return True


@pytest.mark.asyncio
async def test_get_organization_audit_logs_success() -> None:
    audit_repo = InMemoryAuditLogRepository()
    org_repo = InMemoryOrgRepo()
    user_repo = InMemoryUserRepo()
    details_repo = InMemoryMemberDetailsRepo()

    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Acme Health", slug="acme-health")
    await org_repo.save(org)

    user_id = uuid.uuid4()
    user = User(id=user_id, email="employee@acme.com")
    await user_repo.save(user)

    details = MemberDetails(
        user_id=user_id,
        date_of_birth=date(1990, 1, 1),
        first_name="John",
        last_name="Doe",
    )
    await details_repo.save(details)

    log1 = AuditLog.create(
        action="CONSENT_ACCEPTED",
        resource_type="USER_CONSENT",
        user_id=user_id,
        organization_id=org_id,
        details={"form_type": "sleep"},
    )
    await audit_repo.log(log1)

    use_case = GetOrganizationAuditLogsUseCase(
        audit_log_repository=audit_repo,
        organization_repository=org_repo,
        user_repository=user_repo,
        member_details_repository=details_repo,
    )

    res = await use_case.execute(organization_id=org_id)
    assert res.total == 1
    assert len(res.items) == 1
    assert res.items[0].action == "CONSENT_ACCEPTED"
    assert res.items[0].user_email == "employee@acme.com"
    assert res.items[0].user_name == "John Doe"


@pytest.mark.asyncio
async def test_get_organization_audit_logs_not_found() -> None:
    audit_repo = InMemoryAuditLogRepository()
    org_repo = InMemoryOrgRepo()
    user_repo = InMemoryUserRepo()
    details_repo = InMemoryMemberDetailsRepo()

    use_case = GetOrganizationAuditLogsUseCase(
        audit_log_repository=audit_repo,
        organization_repository=org_repo,
        user_repository=user_repo,
        member_details_repository=details_repo,
    )

    with pytest.raises(OrganizationNotFoundError):
        await use_case.execute(organization_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_get_organization_compliance_summary() -> None:
    audit_repo = InMemoryAuditLogRepository()
    org_repo = InMemoryOrgRepo()
    membership_repo = InMemoryMembershipRepo()

    org_id = uuid.uuid4()
    org = Organization(id=org_id, name="Health Corp", slug="health-corp")
    await org_repo.save(org)

    user1 = uuid.uuid4()
    user2 = uuid.uuid4()
    await membership_repo.save(
        Membership(user_id=user1, organization_id=org_id, roles=[OrgRole.MEMBER])
    )
    await membership_repo.save(
        Membership(user_id=user2, organization_id=org_id, roles=[OrgRole.MEMBER])
    )

    await audit_repo.log(
        AuditLog.create(
            action="CONSENT_ACCEPTED",
            resource_type="USER_CONSENT",
            user_id=user1,
            organization_id=org_id,
        )
    )
    await audit_repo.log(
        AuditLog.create(
            action="CONSENT_REVOKED",
            resource_type="USER_CONSENT",
            user_id=user1,
            organization_id=org_id,
        )
    )
    await audit_repo.log(
        AuditLog.create(
            action="DATA_EXPORTED",
            resource_type="MEMBER_DATA",
            user_id=user2,
            organization_id=org_id,
        )
    )

    use_case = GetOrganizationComplianceSummaryUseCase(
        audit_log_repository=audit_repo,
        organization_repository=org_repo,
        membership_repository=membership_repo,
    )

    summary = await use_case.execute(organization_id=org_id)
    assert summary.total_audit_events == 3
    assert summary.consent_accepted_count == 1
    assert summary.consent_revoked_count == 1
    assert summary.data_exported_count == 1
    assert summary.audited_members_count == 2
