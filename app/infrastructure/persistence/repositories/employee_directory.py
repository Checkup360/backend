import unicodedata
import uuid

from sqlalchemy import (
    ColumnElement,
    String,
    and_,
    case,
    false,
    func,
    literal,
    null,
    or_,
    select,
    true,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.domain.entities.department import Department
from app.domain.entities.employee_summary import EmployeeSummary
from app.domain.services.employee_search import normalize_search_term
from app.domain.services.employee_status import (
    INACTIVE,
    ONBOARDING,
    PENDING_ASSESSMENTS,
    UP_TO_DATE,
)
from app.domain.value_objects import (
    EmployeeDirectoryQuery,
    MembershipState,
    OrgRole,
    ScoreFilter,
)
from app.infrastructure.persistence.models.assessment_submission import (
    AssessmentSubmissionModel,
)
from app.infrastructure.persistence.models.department import (
    Department as DepartmentORM,
)
from app.infrastructure.persistence.models.member_details import (
    MemberDetails as MemberDetailsORM,
)
from app.infrastructure.persistence.models.member_health_data import MemberHealthData
from app.infrastructure.persistence.models.member_overall_score import (
    MemberOverallScoreModel,
)
from app.infrastructure.persistence.models.membership import Membership as MembershipORM
from app.infrastructure.persistence.models.risk_score import RiskScoreModel
from app.infrastructure.persistence.models.user import User as UserORM

UNASSIGNED_DEPARTMENT = "Unassigned"
COMPLETED_SUBMISSION = "completed"


def _build_accent_folding() -> tuple[str, str]:
    """Latin letters with a diacritic and the plain letter they fold to."""
    accented, plain = [], []
    for code_point in range(0xC0, 0x180):
        character = chr(code_point).lower()
        base = unicodedata.normalize("NFKD", character)[0]
        if character != base and base.isascii() and character not in accented:
            accented.append(character)
            plain.append(base)
    return "".join(accented), "".join(plain)


_ACCENTED_LETTERS, _PLAIN_LETTERS = _build_accent_folding()


def _fold(column: ColumnElement) -> ColumnElement:
    """Lowercase and strip accents so it matches ``normalize_search_term``."""
    return func.translate(
        func.lower(column), _ACCENTED_LETTERS, _PLAIN_LETTERS, type_=String
    )


class SQLAlchemyEmployeeDirectoryRepository:
    """Answers the employee directory with a single filtered, paginated query."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self, organization_id: uuid.UUID, query: EmployeeDirectoryQuery
    ) -> tuple[list[EmployeeSummary], int]:
        scores = self._latest_scores(organization_id)
        risk_scores = self._latest_risk_scores(organization_id)

        count_statement = select(func.count()).select_from(
            self._filtered(
                organization_id, query, scores, risk_scores, MembershipORM.user_id
            ).subquery()
        )
        total = await self.db.scalar(count_statement) or 0
        if total == 0:
            return [], 0

        statement = self._filtered(
            organization_id,
            query,
            scores,
            risk_scores,
            MembershipORM.user_id,
            UserORM.email,
            MembershipORM.roles,
            self._status(query.required_form_fields).label("status"),
            MemberDetailsORM.first_name,
            MemberDetailsORM.last_name,
            MemberDetailsORM.avatar_url,
            DepartmentORM,
            scores.c.overall_health_index,
            func.coalesce(scores.c.evaluated_at, risk_scores.c.evaluated_at).label(
                "last_assessment"
            ),
        ).order_by(UserORM.email, MembershipORM.user_id)
        if query.page is not None:
            statement = statement.offset((query.page - 1) * query.page_size).limit(
                query.page_size
            )
        result = await self.db.execute(statement)
        return [self._to_summary(row) for row in result.all()], total

    def _filtered(
        self,
        organization_id: uuid.UUID,
        query: EmployeeDirectoryQuery,
        scores,
        risk_scores,
        *columns,
    ) -> Select:
        statement = (
            select(*columns)
            .select_from(MembershipORM)
            .join(UserORM, UserORM.id == MembershipORM.user_id)
            .outerjoin(MemberDetailsORM, MemberDetailsORM.user_id == UserORM.id)
            .outerjoin(
                DepartmentORM,
                and_(
                    DepartmentORM.id == MembershipORM.department_id,
                    DepartmentORM.organization_id == MembershipORM.organization_id,
                ),
            )
            .outerjoin(scores, scores.c.user_id == UserORM.id)
            .outerjoin(risk_scores, risk_scores.c.user_id == UserORM.id)
            .where(MembershipORM.organization_id == organization_id)
        )
        for condition in self._conditions(query, scores):
            statement = statement.where(condition)
        return statement

    def _conditions(
        self, query: EmployeeDirectoryQuery, latest_scores
    ) -> list[ColumnElement]:
        conditions: list[ColumnElement] = []
        if query.roles:
            conditions.append(
                or_(*[MembershipORM.roles.contains([role]) for role in query.roles])
            )
        role_count = func.coalesce(func.cardinality(MembershipORM.roles), 0)
        if query.state == MembershipState.ACTIVE:
            conditions.append(role_count > 0)
        elif query.state == MembershipState.INACTIVE:
            conditions.append(role_count == 0)
        if query.department_id is not None:
            conditions.append(MembershipORM.department_id == query.department_id)
        if query.status is not None:
            conditions.append(
                self._status(query.required_form_fields) == query.status.lower()
            )
        if query.score_filter == ScoreFilter.SCORED:
            conditions.append(latest_scores.c.user_id.is_not(None))
        elif query.score_filter == ScoreFilter.UNSCORED:
            conditions.append(latest_scores.c.user_id.is_(None))
        search_condition = self._search_condition(query.search)
        if search_condition is not None:
            conditions.append(search_condition)
        return conditions

    @staticmethod
    def _search_condition(search: str | None) -> ColumnElement | None:
        term = normalize_search_term(search or "")
        if not term:
            return None
        first_name = func.coalesce(MemberDetailsORM.first_name, "")
        last_name = func.coalesce(MemberDetailsORM.last_name, "")
        searchable = (
            UserORM.email,
            func.coalesce(DepartmentORM.name, UNASSIGNED_DEPARTMENT),
            first_name,
            last_name,
            first_name.concat(" ").concat(last_name),
            last_name.concat(" ").concat(first_name),
        )
        return or_(
            *[_fold(value).contains(term, autoescape=True) for value in searchable]
        )

    @staticmethod
    def _status(required_form_fields: dict[str, list[str]]) -> ColumnElement:
        """SQL form of ``determine_employee_status`` (domain/services)."""
        role_count = func.coalesce(func.cardinality(MembershipORM.roles), 0)
        is_member = MembershipORM.roles.contains([OrgRole.MEMBER])
        onboarded = MemberDetailsORM.user_id.is_not(None)
        completed_forms = [
            SQLAlchemyEmployeeDirectoryRepository._form_completed(form_type, fields)
            for form_type, fields in required_form_fields.items()
        ]
        return case(
            (role_count == 0, literal(INACTIVE)),
            (~is_member, null()),
            (~onboarded, literal(ONBOARDING)),
            (and_(true(), *completed_forms), literal(UP_TO_DATE)),
            else_=literal(PENDING_ASSESSMENTS),
        )

    @staticmethod
    def _form_completed(form_type: str, fields: list[str]) -> ColumnElement:
        submitted = (
            select(1)
            .select_from(AssessmentSubmissionModel)
            .where(
                AssessmentSubmissionModel.user_id == MembershipORM.user_id,
                AssessmentSubmissionModel.form_type == form_type,
                AssessmentSubmissionModel.status == COMPLETED_SUBMISSION,
            )
            .correlate(MembershipORM)
            .exists()
        )
        columns = [
            getattr(MemberHealthData, name)
            for name in fields
            if hasattr(MemberHealthData, name)
        ]
        if not columns:
            return or_(submitted, false())
        filled = (
            select(1)
            .select_from(MemberHealthData)
            .where(
                MemberHealthData.user_id == MembershipORM.user_id,
                or_(*[column.is_not(None) for column in columns]),
            )
            .correlate(MembershipORM)
            .exists()
        )
        return or_(submitted, filled)

    @staticmethod
    def _latest_scores(organization_id: uuid.UUID):
        return (
            select(
                MemberOverallScoreModel.user_id,
                MemberOverallScoreModel.overall_health_index,
                MemberOverallScoreModel.evaluated_at,
            )
            .where(MemberOverallScoreModel.organization_id == organization_id)
            .distinct(MemberOverallScoreModel.user_id)
            .order_by(
                MemberOverallScoreModel.user_id,
                MemberOverallScoreModel.evaluated_at.desc(),
            )
            .subquery("latest_overall_scores")
        )

    @staticmethod
    def _latest_risk_scores(organization_id: uuid.UUID):
        """Last evaluation of users that predate persisted overall scores."""
        organization_members = select(MembershipORM.user_id).where(
            MembershipORM.organization_id == organization_id
        )
        return (
            select(
                RiskScoreModel.user_id,
                func.max(RiskScoreModel.evaluated_at).label("evaluated_at"),
            )
            .where(RiskScoreModel.user_id.in_(organization_members))
            .group_by(RiskScoreModel.user_id)
            .subquery("latest_risk_scores")
        )

    @staticmethod
    def _to_summary(row) -> EmployeeSummary:
        department = row.Department
        return EmployeeSummary(
            user_id=row.user_id,
            email=row.email,
            roles=[
                role if isinstance(role, OrgRole) else OrgRole(role)
                for role in row.roles
            ],
            status=row.status,
            first_name=row.first_name or None,
            last_name=row.last_name or None,
            avatar_url=row.avatar_url,
            department=(
                Department(
                    id=department.id,
                    organization_id=department.organization_id,
                    name=department.name,
                    slug=department.slug,
                    created_at=department.created_at,
                    updated_at=department.updated_at,
                )
                if department
                else None
            ),
            last_assessment=row.last_assessment,
            overall_health_index=row.overall_health_index,
        )
