from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.dto import AuthenticatedUser
from app.presentation.api.authorization import (
    require_active_member,
    require_health_data_consent,
    require_member_role,
)
from app.presentation.api.dependencies import (
    get_current_user,
    get_submit_assessment_use_case,
    get_get_assessments_use_case,
    get_organization_service,
    get_assessment_submissions_use_case,
    get_member_overall_score_repository,
)
from app.domain.entities.member_overall_score import MemberOverallScore
from app.domain.repositories.member_overall_score import MemberOverallScoreRepository
from app.application.use_cases.assessments.submit_assessment import (
    SubmitAssessmentUseCase,
)
from app.application.use_cases.assessments.get_assessments import GetAssessmentsUseCase
from app.application.use_cases.organizations.organization_service import (
    OrganizationService,
)
from app.domain.services.health_index_classification import classify_health_index
from app.domain.services.risk_score_calculator import (
    calculate_weighted_overall_score,
)
from app.application.dto.risk_scoring import HealthDataDTO
from app.presentation.api.request_models.assessments import ClinicalAssessmentRequest
from app.presentation.api.response_models.assessments import (
    AssessmentsResponse,
    AssessmentResultResponse,
    AssessmentSessionResponse,
)
from app.presentation.api.response_models.assessment_submissions import (
    AssessmentSubmissionAnswersResponse,
    AssessmentSubmissionDetailResponse,
    AssessmentSubmissionListResponse,
    AssessmentSubmissionScoreResponse,
    AssessmentSubmissionSummaryResponse,
)
from app.application.use_cases.assessments.get_submissions import (
    GetAssessmentSubmissionsUseCase,
)

router = APIRouter(
    prefix="/members/me/assessments",
    tags=["assessments"],
    dependencies=[Depends(require_member_role)],
)
submissions_router = APIRouter(
    prefix="/members/me/assessment-submissions",
    tags=["assessment-submissions"],
    dependencies=[Depends(require_member_role)],
)


def _format_score_display_name(name: str) -> str:
    lower = name.lower()
    if "findrisc" in lower or "diabetes" in lower:
        return "Diabetes"
    if ("stop" in lower and "bang" in lower) or "sleep" in lower:
        return "Sleep Apnea"
    if "phq" in lower or "depression" in lower or "mood" in lower:
        return "Mood & Well-being"
    if "metabolic" in lower:
        return "Metabolic Health"
    if "eoss" in lower or "obesity" in lower:
        return "Obesity Impact"
    if "score2" in lower or "cardiovascular" in lower:
        return "Cardiovascular"
    if "nordic" in lower or "nmq" in lower or "musculoskeletal" in lower:
        return "Musculoskeletal"
    if "audit" in lower or "alcohol" in lower:
        return "Alcohol Habits"
    if "pss" in lower or "stress" in lower:
        return "Stress & Burnout"
    return name


def build_assessment_sessions(
    results: list[AssessmentResultResponse],
    score_weights: dict[str, float] | None = None,
    risk_thresholds: dict[str, float] | None = None,
    persisted_history: list[MemberOverallScore] | None = None,
) -> list[AssessmentSessionResponse]:
    if not results:
        return []

    sorted_results = sorted(
        results,
        key=lambda r: r.evaluated_at.timestamp() if r.evaluated_at else 0,
        reverse=True,
    )

    # Index persisted history by evaluated_at timestamp bucket or submission_id if available
    persisted_by_ts: dict[int, MemberOverallScore] = {}
    if persisted_history:
        for p in persisted_history:
            if p.evaluated_at:
                p_ts = (int(p.evaluated_at.timestamp()) // 2) * 2
                persisted_by_ts[p_ts] = p

    buckets: dict[int, list[AssessmentResultResponse]] = {}
    for r in sorted_results:
        raw_ts = int(r.evaluated_at.timestamp()) if r.evaluated_at else 0
        bucket_ts = (raw_ts // 2) * 2
        if bucket_ts not in buckets:
            buckets[bucket_ts] = []
        buckets[bucket_ts].append(r)

    bucket_timestamps = sorted(buckets.keys(), reverse=True)
    sessions: list[AssessmentSessionResponse] = []

    for idx, b_ts in enumerate(bucket_timestamps):
        b_results = buckets[b_ts]
        primary_eval_at = b_results[0].evaluated_at or datetime.fromtimestamp(
            b_ts, tz=timezone.utc
        )

        active_at_time: dict[str, AssessmentResultResponse] = {}
        for r in sorted_results:
            if r.evaluated_at and r.evaluated_at <= primary_eval_at:
                s_key = r.score_name.lower()
                if s_key not in active_at_time:
                    active_at_time[s_key] = r

        session_results = list(active_at_time.values())

        # Use persisted score if available
        matched_persisted: MemberOverallScore | None = None
        if b_ts in persisted_by_ts:
            matched_persisted = persisted_by_ts[b_ts]
        elif persisted_history:
            target_ts = primary_eval_at.timestamp()
            for p in persisted_history:
                if p.evaluated_at and abs(p.evaluated_at.timestamp() - target_ts) <= 5:
                    matched_persisted = p
                    break

        if (
            matched_persisted is not None
            and matched_persisted.overall_health_index is not None
        ):
            overall_health_index = matched_persisted.overall_health_index
            if risk_thresholds is not None:
                overall_risk_level = classify_health_index(
                    matched_persisted.overall_health_index, risk_thresholds
                )
            else:
                overall_risk_level = matched_persisted.risk_level
        else:
            calc_score, calc_risk = calculate_weighted_overall_score(
                session_results, score_weights, risk_thresholds=risk_thresholds
            )
            overall_health_index = calc_score
            overall_risk_level = calc_risk

        session_id = f"session_{b_ts}_{idx}"
        sessions.append(
            AssessmentSessionResponse(
                id=session_id,
                evaluated_at=primary_eval_at,
                overall_health_index=overall_health_index,
                overall_risk_level=overall_risk_level,
                results=session_results,
            )
        )

    return sessions


def build_assessments_response(
    results: list[AssessmentResultResponse],
    page: int = 1,
    limit: int = 10,
    score_weights: dict[str, float] | None = None,
    risk_thresholds: dict[str, float] | None = None,
    latest_overall: MemberOverallScore | None = None,
    persisted_history: list[MemberOverallScore] | None = None,
) -> AssessmentsResponse:
    if risk_thresholds is not None:
        normalized_results = [
            AssessmentResultResponse(
                score_id=r.score_id,
                score_name=r.score_name,
                risk_level=(
                    classify_health_index(r.health_index, risk_thresholds)
                    if r.health_index is not None
                    else r.risk_level
                ),
                raw_value=r.raw_value,
                health_index=r.health_index,
                explanation=r.explanation,
                contributing_factors=r.contributing_factors,
                attention_flags=r.attention_flags,
                evaluated_at=r.evaluated_at,
            )
            for r in results
        ]
    else:
        normalized_results = results

    all_sessions = build_assessment_sessions(
        normalized_results,
        score_weights,
        risk_thresholds=risk_thresholds,
        persisted_history=persisted_history,
    )
    total_sessions = len(all_sessions)

    if latest_overall is not None and latest_overall.overall_health_index is not None:
        current_overall_score = latest_overall.overall_health_index
        if risk_thresholds is not None:
            current_overall_risk_level = classify_health_index(
                latest_overall.overall_health_index, risk_thresholds
            )
        else:
            current_overall_risk_level = latest_overall.risk_level
    else:
        calc_score, calc_risk = calculate_weighted_overall_score(
            normalized_results, score_weights, risk_thresholds=risk_thresholds
        )
        current_overall_score = calc_score
        current_overall_risk_level = calc_risk

    start = (page - 1) * limit
    paginated_sessions = all_sessions[start : start + limit]

    latest_results_map: dict[str, AssessmentResultResponse] = {}
    for r in normalized_results:
        s_key = r.score_name.lower()
        if s_key not in latest_results_map:
            latest_results_map[s_key] = r
        else:
            time_new = r.evaluated_at.timestamp() if r.evaluated_at else 0
            time_old = (
                latest_results_map[s_key].evaluated_at.timestamp()
                if latest_results_map[s_key].evaluated_at
                else 0
            )
            if time_new > time_old:
                latest_results_map[s_key] = r
    latest_results = list(latest_results_map.values())

    return AssessmentsResponse(
        overall_health_index=current_overall_score,
        overall_risk_level=current_overall_risk_level,
        risk_thresholds=risk_thresholds,
        total_sessions=total_sessions,
        page=page,
        limit=limit,
        sessions=paginated_sessions,
        results=latest_results,
    )


@router.post("/evaluate", response_model=AssessmentsResponse)
async def evaluate_assessments(
    body: ClinicalAssessmentRequest,
    user: AuthenticatedUser = Depends(require_active_member),
    _consent: AuthenticatedUser = Depends(require_health_data_consent),
    use_case: SubmitAssessmentUseCase = Depends(get_submit_assessment_use_case),
    organization_service: OrganizationService = Depends(get_organization_service),
) -> AssessmentsResponse:

    # Map request model to HealthDataDTO
    health_data = HealthDataDTO(
        age=body.age,
        sex=body.sex,
        height=body.height,
        weight=body.weight,
        waist_circumference=body.waist_circumference,
        triglycerides=body.triglycerides,
        total_cholesterol=body.total_cholesterol,
        hdl_cholesterol=body.hdl_cholesterol,
        systolic_blood_pressure=body.systolic_blood_pressure,
        diastolic_blood_pressure=body.diastolic_blood_pressure,
        fasting_glucose=body.fasting_glucose,
        glucose_lowering_medication=body.glucose_lowering_medication,
        neck_circumference=body.neck_circumference,
        snoring=body.snoring,
        tired=body.tired,
        observed_apnea=body.observed_apnea,
        smoker=body.smoker,
        hypertension_medication=body.hypertension_medication,
        daily_physical_activity=body.daily_physical_activity,
        fruits_vegetables=body.fruits_vegetables,
        previous_high_glucose=body.previous_high_glucose,
        family_diabetes=body.family_diabetes,
        little_interest=body.little_interest,
        feeling_down=body.feeling_down,
        sleep_trouble=body.sleep_trouble,
        tired_energy=body.tired_energy,
        appetite=body.appetite,
        feeling_bad=body.feeling_bad,
        concentration=body.concentration,
        psychomotor=body.psychomotor,
        self_harm_thoughts=body.self_harm_thoughts,
        eoss_physical_health_stage=body.eoss_physical_health_stage,
        eoss_mental_health_stage=body.eoss_mental_health_stage,
        eoss_functional_stage=body.eoss_functional_stage,
    )

    try:
        results = await use_case.execute(
            user_id=user.id,
            health_data=health_data,
            target_scores=[
                "stop_bang",
                "findrisc",
                "phq9",
                "metabolic_syndrome",
                "eoss",
                "score2",
            ],
            organization_id=user.membership.organization_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # Map DTOs to response models
    response_results = [
        AssessmentResultResponse(
            score_id=res.score_id,
            score_name=_format_score_display_name(res.score_name),
            risk_level=res.risk_level,
            raw_value=res.raw_value,
            health_index=res.health_index,
            explanation=res.explanation,
            contributing_factors=res.contributing_factors,
            attention_flags=res.attention_flags,
            evaluated_at=getattr(res, "evaluated_at", None)
            or datetime.now(timezone.utc),
        )
        for res in results
    ]

    score_weights = None
    risk_thresholds = None
    if user.membership and user.membership.organization_id:
        try:
            (
                score_weights,
                risk_thresholds,
            ) = await organization_service.get_score_weights_and_thresholds(
                user.membership.organization_id
            )
        except Exception:
            score_weights = None
            risk_thresholds = None

    return build_assessments_response(
        response_results,
        page=1,
        limit=10,
        score_weights=score_weights,
        risk_thresholds=risk_thresholds,
    )


@router.get("", response_model=AssessmentsResponse)
async def get_assessments(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    use_case: GetAssessmentsUseCase = Depends(get_get_assessments_use_case),
    organization_service: OrganizationService = Depends(get_organization_service),
    member_overall_score_repo: MemberOverallScoreRepository = Depends(
        get_member_overall_score_repository
    ),
) -> AssessmentsResponse:
    if not user.membership or "member" not in user.membership.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    results = await use_case.execute(user_id=user.id)
    latest_overall = await member_overall_score_repo.get_latest_by_user_id(user.id)
    persisted_history = await member_overall_score_repo.get_history_by_user_id(user.id)

    response_results = [
        AssessmentResultResponse(
            score_id=str(res.id),
            score_name=_format_score_display_name(res.score_name),
            risk_level=res.risk_level,
            raw_value=res.raw_value,
            health_index=res.health_index,
            explanation=res.explanation,
            contributing_factors=res.contributing_factors,
            attention_flags=res.attention_flags,
            evaluated_at=res.evaluated_at,
        )
        for res in results
    ]

    score_weights = None
    risk_thresholds = None
    if user.membership and user.membership.organization_id:
        try:
            (
                score_weights,
                risk_thresholds,
            ) = await organization_service.get_score_weights_and_thresholds(
                user.membership.organization_id
            )
        except Exception:
            score_weights = None
            risk_thresholds = None

    return build_assessments_response(
        response_results,
        page=page,
        limit=limit,
        score_weights=score_weights,
        risk_thresholds=risk_thresholds,
        latest_overall=latest_overall,
        persisted_history=persisted_history,
    )


def _submission_detail_response(submission, scores):
    answer_fields = {
        field: getattr(submission, field)
        for field in AssessmentSubmissionAnswersResponse.model_fields
    }
    return AssessmentSubmissionDetailResponse(
        id=submission.id,
        form_type=submission.form_type,
        form_version=submission.form_version,
        status=submission.status,
        submitted_at=submission.submitted_at,
        answers=AssessmentSubmissionAnswersResponse(**answer_fields),
        scores=[
            AssessmentSubmissionScoreResponse(
                score_id=score.id,
                score_name=_format_score_display_name(score.score_name),
                risk_level=score.risk_level,
                raw_value=score.raw_value,
                health_index=score.health_index,
                explanation=score.explanation,
                contributing_factors=score.contributing_factors,
                attention_flags=score.attention_flags,
                evaluated_at=score.evaluated_at,
            )
            for score in scores
        ],
    )


@submissions_router.get("", response_model=AssessmentSubmissionListResponse)
async def list_my_assessment_submissions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    use_case: GetAssessmentSubmissionsUseCase = Depends(
        get_assessment_submissions_use_case
    ),
):
    if not user.membership or "member" not in user.membership.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    items, total = await use_case.list_for_user(user.id, page, limit)
    return AssessmentSubmissionListResponse(
        items=[
            AssessmentSubmissionSummaryResponse.model_validate(
                item, from_attributes=True
            )
            for item in items
        ],
        page=page,
        limit=limit,
        total=total,
        has_next=page * limit < total,
    )


@submissions_router.get(
    "/{submission_id}", response_model=AssessmentSubmissionDetailResponse
)
async def get_my_assessment_submission(
    submission_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    use_case: GetAssessmentSubmissionsUseCase = Depends(
        get_assessment_submissions_use_case
    ),
):
    if not user.membership or "member" not in user.membership.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    result = await use_case.get_detail(submission_id)
    if (
        result is None
        or result[0].user_id != user.id
        or result[0].organization_id != user.membership.organization_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return _submission_detail_response(*result)
