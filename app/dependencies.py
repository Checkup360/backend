from fastapi import Depends

from app.domain.services.invite import InviteService
from app.domain.services.member_details import MemberDetailsService
from app.domain.services.membership import MembershipService
from app.domain.services.organization import OrganizationService
from app.persistence.database import get_db
from app.persistence.repositories.invite import InviteRepository
from app.persistence.repositories.member_details import MemberDetailsRepository
from app.persistence.repositories.membership import MembershipRepository
from app.persistence.repositories.organization import OrganizationRepository
from app.persistence.repositories.user import UserRepository


async def get_invite_repository(
    db=Depends(get_db),
) -> InviteRepository:
    return InviteRepository(db)


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
    user_repo: UserRepository = Depends(get_user_repository),
) -> InviteService:
    return InviteService(invite_repo, membership_repo, user_repo)


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
