from typing import AsyncGenerator
import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces import EmailSender
from app.domain.services.time_provider import TimeProvider
from app.infrastructure.time.system_time_provider import SystemTimeProvider
from app.application.dto import AuthenticatedUser
from app.domain.entities import Membership
from app.application.use_cases.invitations import (
    DeleteInvites,
    InviteUrlBuilder,
    ListInvites,
)
from app.application.interfaces.risk_scoring_service import RiskScoringService
from app.infrastructure.external.motor_api_adapter import HttpMotorScoringAdapter
from app.application.use_cases.departments.department_service import DepartmentService
from app.domain.services.invite import InviteService
from app.application.use_cases.members.member_health_data_service import (
    MemberHealthDataService,
)
from app.application.use_cases.members.member_details_service import (
    MemberDetailsService,
)
from app.application.use_cases.memberships.membership_service import MembershipService
from app.application.use_cases.organizations.organization_service import (
    OrganizationService,
)
from app.application.use_cases.assessments.submit_assessment import (
    SubmitAssessmentUseCase,
)
from app.application.use_cases.assessments.get_assessments import GetAssessmentsUseCase
from app.application.use_cases.assessments.recalculate_member_scores import (
    RecalculateMemberScoresUseCase,
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
from app.infrastructure.persistence.repositories.risk_score import (
    SQLAlchemyRiskScoreRepository,
)
from app.infrastructure.persistence.repositories.user import UserRepository
from app.infrastructure.persistence.repositories.member_health_data import (
    SQLAlchemyMemberHealthDataRepository,
)
from app.domain.repositories.member_health_data import MemberHealthDataRepository
from app.domain.repositories.risk_score import RiskScoreRepository
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


async def get_member_health_data_repository(
    db=Depends(get_db),
) -> MemberHealthDataRepository:
    return SQLAlchemyMemberHealthDataRepository(db)


async def get_organization_repository(
    db=Depends(get_db),
) -> OrganizationRepository:
    return OrganizationRepository(db)


async def get_user_repository(db=Depends(get_db)):
    return UserRepository(db)


def get_time_provider() -> TimeProvider:
    return SystemTimeProvider()


async def get_invite_service(
    invite_repo: InviteRepository = Depends(get_invite_repository),
    membership_repo: MembershipRepository = Depends(get_membership_repository),
    department_repo: DepartmentRepository = Depends(get_department_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    time_provider: TimeProvider = Depends(get_time_provider),
) -> InviteService:
    return InviteService(
        invite_repo, membership_repo, user_repo, department_repo, time_provider
    )


async def get_membership_service(
    membership_repo: MembershipRepository = Depends(get_membership_repository),
    org_repo: OrganizationRepository = Depends(get_organization_repository),
) -> MembershipService:
    return MembershipService(membership_repo, org_repo)


async def get_member_details_service(
    repo: MemberDetailsRepository = Depends(get_member_details_repository),
    time_provider: TimeProvider = Depends(get_time_provider),
) -> MemberDetailsService:
    return MemberDetailsService(repo, time_provider)


async def get_member_health_data_service(
    repo: MemberHealthDataRepository = Depends(get_member_health_data_repository),
) -> MemberHealthDataService:
    return MemberHealthDataService(repo)


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


async def get_risk_scoring_service() -> AsyncGenerator[RiskScoringService, None]:
    async with httpx.AsyncClient() as client:
        yield HttpMotorScoringAdapter(settings.motor_api_url, client)


async def get_risk_score_repository(
    db: AsyncSession = Depends(get_db),
) -> RiskScoreRepository:
    return SQLAlchemyRiskScoreRepository(db)


async def get_submit_assessment_use_case(
    risk_scoring_service: RiskScoringService = Depends(get_risk_scoring_service),
    member_details_repository: MemberDetailsRepository = Depends(
        get_member_details_repository
    ),
    risk_score_repository: RiskScoreRepository = Depends(get_risk_score_repository),
    time_provider: TimeProvider = Depends(get_time_provider),
) -> SubmitAssessmentUseCase:
    return SubmitAssessmentUseCase(
        risk_scoring_service,
        member_details_repository,
        risk_score_repository,
        time_provider,
    )


async def get_get_assessments_use_case(
    risk_score_repository: RiskScoreRepository = Depends(get_risk_score_repository),
) -> GetAssessmentsUseCase:
    return GetAssessmentsUseCase(risk_score_repository)


async def get_recalculate_member_scores_use_case(
    health_data_repo: MemberHealthDataRepository = Depends(
        get_member_health_data_repository
    ),
    details_repo: MemberDetailsRepository = Depends(get_member_details_repository),
    risk_score_repo: RiskScoreRepository = Depends(get_risk_score_repository),
    risk_scoring_service: RiskScoringService = Depends(get_risk_scoring_service),
) -> RecalculateMemberScoresUseCase:
    return RecalculateMemberScoresUseCase(
        health_data_repo, details_repo, risk_score_repo, risk_scoring_service
    )
