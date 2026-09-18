from typing import AsyncGenerator
import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces import EmailSender
from app.domain.services.time_provider import TimeProvider
from app.domain.services.form_registry import FormRegistry
from app.infrastructure.time.system_time_provider import SystemTimeProvider
from app.application.dto import AuthenticatedUser
from app.domain.entities import Membership
from app.application.use_cases.invitations import (
    DeleteInvites,
    InviteUrlBuilder,
    ListInvites,
)
from app.application.interfaces.risk_scoring_service import RiskScoringService
from app.infrastructure.external.engine_api_adapter import HttpEngineScoringAdapter
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
from app.application.use_cases.assessments.get_active_member_forms import (
    GetActiveMemberFormsUseCase,
)
from app.application.use_cases.assessments.get_submissions import (
    GetAssessmentSubmissionsUseCase,
)
from app.application.use_cases.assessments.save_submission import (
    SaveAssessmentSubmissionUseCase,
)
from app.application.use_cases.admin.list_sysadmins import ListSysadminsUseCase
from app.application.use_cases.assessments.recalculate_member_scores import (
    RecalculateMemberScoresUseCase,
)
from app.application.use_cases.members.get_member_risk_priorities import (
    GetMemberRiskPrioritiesUseCase,
)
from app.application.interfaces.file_storage import FileStorage
from app.infrastructure.storage.local_storage import LocalDiskFileStorage
from app.application.use_cases.members.upload_member_avatar import (
    UploadMemberAvatarUseCase,
)
from app.application.use_cases.members.delete_member_avatar import (
    DeleteMemberAvatarUseCase,
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
from app.infrastructure.persistence.repositories.assessment_submission import (
    SQLAlchemyAssessmentSubmissionRepository,
)
from app.infrastructure.persistence.repositories.user import UserRepository
from app.infrastructure.persistence.repositories.member_health_data import (
    SQLAlchemyMemberHealthDataRepository,
)
from app.domain.repositories.member_overall_score import (
    MemberOverallScoreRepository,
)
from app.domain.repositories.organization_score_weights import (
    OrganizationScoreWeightsRepository,
)
from app.infrastructure.persistence.repositories.member_overall_score import (
    SQLAlchemyMemberOverallScoreRepository,
)
from app.infrastructure.persistence.repositories.organization_score_weights import (
    OrganizationScoreWeightsRepository as SQLAlchemyOrganizationScoreWeightsRepository,
)
from app.domain.repositories.member_health_data import MemberHealthDataRepository
from app.domain.repositories.risk_score import RiskScoreRepository
from app.domain.repositories.analytics import AnalyticsRepository
from app.infrastructure.persistence.repositories.analytics import (
    AnalyticsRepositoryImpl,
)
from app.application.use_cases.organizations import (
    DeleteOrganizationLogoUseCase,
    GetOrganizationAnalyticsUseCase,
    UploadOrganizationLogoUseCase,
)
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
    organization_logo_url = None
    if user.membership is not None:
        membership = Membership(
            user_id=user.membership.user_id,
            organization_id=user.membership.organization_id,
            roles=list(user.membership.roles),
            department_id=user.membership.department_id,
        )
        organization_name = user.membership.organization.name
        organization_logo_url = user.membership.organization.logo_url
    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        is_superuser=user.is_superuser,
        membership=membership,
        organization_name=organization_name,
        organization_logo_url=organization_logo_url,
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


def get_form_registry() -> FormRegistry:
    return FormRegistry()


async def get_assessment_submission_repository(
    db: AsyncSession = Depends(get_db),
) -> SQLAlchemyAssessmentSubmissionRepository:
    return SQLAlchemyAssessmentSubmissionRepository(db)


async def get_member_details_service(
    repo: MemberDetailsRepository = Depends(get_member_details_repository),
    time_provider: TimeProvider = Depends(get_time_provider),
    health_data_repo: MemberHealthDataRepository = Depends(
        get_member_health_data_repository
    ),
    submission_repo: SQLAlchemyAssessmentSubmissionRepository = Depends(
        get_assessment_submission_repository
    ),
    form_registry: FormRegistry = Depends(get_form_registry),
) -> MemberDetailsService:
    return MemberDetailsService(
        repo,
        time_provider,
        health_data_repo=health_data_repo,
        submission_repo=submission_repo,
        form_registry=form_registry,
    )


async def get_member_health_data_service(
    repo: MemberHealthDataRepository = Depends(get_member_health_data_repository),
) -> MemberHealthDataService:
    return MemberHealthDataService(repo)


async def get_organization_score_weights_repository(
    db: AsyncSession = Depends(get_db),
) -> OrganizationScoreWeightsRepository:
    return SQLAlchemyOrganizationScoreWeightsRepository(db)


async def get_member_overall_score_repository(
    db: AsyncSession = Depends(get_db),
) -> MemberOverallScoreRepository:
    return SQLAlchemyMemberOverallScoreRepository(db)


async def get_organization_service(
    repo: OrganizationRepository = Depends(get_organization_repository),
    score_weights_repo: OrganizationScoreWeightsRepository = Depends(
        get_organization_score_weights_repository
    ),
) -> OrganizationService:
    return OrganizationService(repo, score_weights_repo=score_weights_repo)


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
        yield HttpEngineScoringAdapter(settings.engine_api_url, client)


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
    assessment_submission_repository: SQLAlchemyAssessmentSubmissionRepository = Depends(
        get_assessment_submission_repository
    ),
) -> SubmitAssessmentUseCase:
    return SubmitAssessmentUseCase(
        risk_scoring_service,
        member_details_repository,
        risk_score_repository,
        time_provider,
        assessment_submission_repository,
    )


async def get_get_assessments_use_case(
    risk_score_repository: RiskScoreRepository = Depends(get_risk_score_repository),
) -> GetAssessmentsUseCase:
    return GetAssessmentsUseCase(risk_score_repository)


async def get_assessment_submissions_use_case(
    submission_repository: SQLAlchemyAssessmentSubmissionRepository = Depends(
        get_assessment_submission_repository
    ),
    risk_score_repository: RiskScoreRepository = Depends(get_risk_score_repository),
) -> GetAssessmentSubmissionsUseCase:
    return GetAssessmentSubmissionsUseCase(submission_repository, risk_score_repository)


async def get_save_assessment_submission_use_case(
    repository: SQLAlchemyAssessmentSubmissionRepository = Depends(
        get_assessment_submission_repository
    ),
) -> SaveAssessmentSubmissionUseCase:
    return SaveAssessmentSubmissionUseCase(repository)


async def get_recalculate_member_scores_use_case(
    health_data_repo: MemberHealthDataRepository = Depends(
        get_member_health_data_repository
    ),
    details_repo: MemberDetailsRepository = Depends(get_member_details_repository),
    risk_score_repo: RiskScoreRepository = Depends(get_risk_score_repository),
    risk_scoring_service: RiskScoringService = Depends(get_risk_scoring_service),
    member_overall_score_repo: MemberOverallScoreRepository = Depends(
        get_member_overall_score_repository
    ),
    membership_repo: MembershipRepository = Depends(get_membership_repository),
    score_weights_repo: OrganizationScoreWeightsRepository = Depends(
        get_organization_score_weights_repository
    ),
) -> RecalculateMemberScoresUseCase:
    return RecalculateMemberScoresUseCase(
        health_data_repo,
        details_repo,
        risk_score_repo,
        risk_scoring_service,
        member_overall_score_repo=member_overall_score_repo,
        membership_repo=membership_repo,
        score_weights_repo=score_weights_repo,
    )


async def get_analytics_repository(
    db: AsyncSession = Depends(get_db),
) -> AnalyticsRepository:
    return AnalyticsRepositoryImpl(db)


async def get_organization_analytics_use_case(
    analytics_repo: AnalyticsRepository = Depends(get_analytics_repository),
    org_repo: OrganizationRepository = Depends(get_organization_repository),
) -> GetOrganizationAnalyticsUseCase:
    return GetOrganizationAnalyticsUseCase(analytics_repo, org_repo)


def get_list_sysadmins_use_case(
    user_repo: UserRepository = Depends(get_user_repository),
    invite_repo: InviteRepository = Depends(get_invite_repository),
) -> ListSysadminsUseCase:
    return ListSysadminsUseCase(user_repo, invite_repo)


async def get_member_risk_priorities_use_case(
    risk_score_repo: RiskScoreRepository = Depends(get_risk_score_repository),
    org_repo: OrganizationRepository = Depends(get_organization_repository),
) -> GetMemberRiskPrioritiesUseCase:
    return GetMemberRiskPrioritiesUseCase(risk_score_repo, org_repo)


def get_file_storage() -> FileStorage:
    return LocalDiskFileStorage(
        base_directory=settings.upload_dir,
        public_url_prefix="/media",
    )


async def get_upload_member_avatar_use_case(
    details_repo: MemberDetailsRepository = Depends(get_member_details_repository),
    file_storage: FileStorage = Depends(get_file_storage),
) -> UploadMemberAvatarUseCase:
    return UploadMemberAvatarUseCase(details_repo, file_storage)


async def get_delete_member_avatar_use_case(
    details_repo: MemberDetailsRepository = Depends(get_member_details_repository),
    file_storage: FileStorage = Depends(get_file_storage),
) -> DeleteMemberAvatarUseCase:
    return DeleteMemberAvatarUseCase(details_repo, file_storage)


async def get_get_active_member_forms_use_case(
    org_repo: OrganizationRepository = Depends(get_organization_repository),
    score_weights_repo: OrganizationScoreWeightsRepository = Depends(
        get_organization_score_weights_repository
    ),
) -> GetActiveMemberFormsUseCase:
    return GetActiveMemberFormsUseCase(
        organization_repository=org_repo,
        score_weights_repository=score_weights_repo,
    )


async def get_upload_organization_logo_use_case(
    org_repo: OrganizationRepository = Depends(get_organization_repository),
    file_storage: FileStorage = Depends(get_file_storage),
) -> UploadOrganizationLogoUseCase:
    return UploadOrganizationLogoUseCase(org_repo, file_storage)


async def get_delete_organization_logo_use_case(
    org_repo: OrganizationRepository = Depends(get_organization_repository),
    file_storage: FileStorage = Depends(get_file_storage),
) -> DeleteOrganizationLogoUseCase:
    return DeleteOrganizationLogoUseCase(org_repo, file_storage)
