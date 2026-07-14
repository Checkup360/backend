from fastapi import Depends

from app.application.interfaces import EmailSender
from app.application.dto import AuthenticatedUser
from app.domain.entities import Membership
from app.application.use_cases.invitations import (
    DeleteInvites,
    InviteUrlBuilder,
    ListInvites,
)
from app.application.use_cases.departments.department_service import DepartmentService
from app.domain.services.invite import InviteService
from app.application.use_cases.members.member_details_service import (
    MemberDetailsService,
)
from app.application.use_cases.memberships.membership_service import MembershipService
from app.application.use_cases.organizations.organization_service import (
    OrganizationService,
)
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.department import DepartmentRepository
from app.infrastructure.persistence.repositories.invite import InviteRepository
from app.infrastructure.persistence.repositories.member_details import (
    MemberDetailsRepository,
)
from app.infrastructure.persistence.repositories.membership import MembershipRepository
from app.infrastructure.persistence.repositories.organization import (
    OrganizationRepository,
)
from app.infrastructure.persistence.repositories.user import UserRepository
from app.infrastructure.email import SmtpEmailSender
from app.infrastructure.config import settings
from app.infrastructure.authentication.machinery.users import current_active_user


async def get_invite_repository(
    db=Depends(get_db),
) -> InviteRepository:
    return InviteRepository(db)


async def get_current_user(user=Depends(current_active_user)) -> AuthenticatedUser:
    membership = None
    organization_name = None
    if user.membership is not None:
        membership = Membership(
            user_id=user.membership.user_id,
            organization_id=user.membership.organization_id,
            roles=list(user.membership.roles),
            department_id=user.membership.department_id,
        )
        organization_name = user.membership.organization.name
    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        is_superuser=user.is_superuser,
        membership=membership,
        organization_name=organization_name,
    )


async def get_department_repository(
    db=Depends(get_db),
) -> DepartmentRepository:
    return DepartmentRepository(db)


async def get_membership_repository(
    db=Depends(get_db),
) -> MembershipRepository:
    return MembershipRepository(db)


async def get_member_details_repository(
    db=Depends(get_db),
) -> MemberDetailsRepository:
    return MemberDetailsRepository(db)


async def get_organization_repository(
    db=Depends(get_db),
) -> OrganizationRepository:
    return OrganizationRepository(db)


async def get_user_repository(db=Depends(get_db)):
    return UserRepository(db)


async def get_invite_service(
    invite_repo: InviteRepository = Depends(get_invite_repository),
    membership_repo: MembershipRepository = Depends(get_membership_repository),
    department_repo: DepartmentRepository = Depends(get_department_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> InviteService:
    return InviteService(invite_repo, membership_repo, user_repo, department_repo)


async def get_membership_service(
    membership_repo: MembershipRepository = Depends(get_membership_repository),
    org_repo: OrganizationRepository = Depends(get_organization_repository),
) -> MembershipService:
    return MembershipService(membership_repo, org_repo)


async def get_member_details_service(
    repo: MemberDetailsRepository = Depends(get_member_details_repository),
) -> MemberDetailsService:
    return MemberDetailsService(repo)


async def get_organization_service(
    repo: OrganizationRepository = Depends(get_organization_repository),
) -> OrganizationService:
    return OrganizationService(repo)


async def get_department_service(
    department_repo: DepartmentRepository = Depends(get_department_repository),
    membership_service: MembershipService = Depends(get_membership_service),
    membership_repo: MembershipRepository = Depends(get_membership_repository),
) -> DepartmentService:
    return DepartmentService(department_repo, membership_service, membership_repo)


def get_email_sender() -> EmailSender:
    return SmtpEmailSender()


def get_invite_url_builder() -> InviteUrlBuilder:
    return InviteUrlBuilder(settings.frontend_url)


def get_list_invites(
    repository: InviteRepository = Depends(get_invite_repository),
) -> ListInvites:
    return ListInvites(repository)


def get_delete_invites(
    repository: InviteRepository = Depends(get_invite_repository),
) -> DeleteInvites:
    return DeleteInvites(repository)
