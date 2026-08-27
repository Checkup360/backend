from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.dto import AuthenticatedUser
from app.presentation.api.dependencies import (
    get_current_user,
    get_submit_assessment_use_case,
    get_get_assessments_use_case,
    get_organization_service,
)
from app.application.use_cases.assessments.submit_assessment import (
    SubmitAssessmentUseCase,
)
from app.application.use_cases.assessments.get_assessments import GetAssessmentsUseCase
from app.application.use_cases.organizations.organization_service import (
    OrganizationService,
)
from app.domain.services.risk_score_calculator import calculate_weighted_overall_score
from app.application.dto.risk_scoring import HealthDataDTO
from app.presentation.api.request_models.assessments import ClinicalAssessmentRequest
from app.presentation.api.response_models.assessments import (
    AssessmentsResponse,
    AssessmentResultResponse,
    AssessmentSessionResponse,
)

router = APIRouter(prefix="/members/me/assessments", tags=["assessments"])


def _format_score_display_name(name: str) -> str:
    lower = name.lower()
    if "findrisc" in lower:
        return "Diabetes"
    if "stop" in lower and "bang" in lower:
        return "Sleep Apnea"
    return name


def compute_overall_summary(
    results: list[AssessmentResultResponse],
    weights: dict[str, float] | None = None,
) -> tuple[float | None, str | None]:
    return calculate_weighted_overall_score(results, weights)


def build_assessment_sessions(
    results: list[AssessmentResultResponse],
    score_weights: dict[str, float] | None = None,
) -> list[AssessmentSessionResponse]:
    if not results:
        return []

    sorted_results = sorted(
        results,
        key=lambda r: r.evaluated_at.timestamp() if r.evaluated_at else 0,
        reverse=True,
    )

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
        overall_score, overall_risk_level = compute_overall_summary(
            session_results, score_weights
        )

        session_id = f"session_{b_ts}_{idx}"
        sessions.append(
            AssessmentSessionResponse(
                id=session_id,
                evaluated_at=primary_eval_at,
                overall_score=overall_score,
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
) -> AssessmentsResponse:
    all_sessions = build_assessment_sessions(results, score_weights)
    total_sessions = len(all_sessions)

    current_overall_score, current_overall_risk_level = compute_overall_summary(
        results, score_weights
    )

    start = (page - 1) * limit
    paginated_sessions = all_sessions[start : start + limit]

    latest_results_map: dict[str, AssessmentResultResponse] = {}
    for r in results:
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
        overall_score=current_overall_score,
        overall_risk_level=current_overall_risk_level,
        total_sessions=total_sessions,
        page=page,
        limit=limit,
        sessions=paginated_sessions,
        results=latest_results,
    )


@router.post("/evaluate", response_model=AssessmentsResponse)
async def evaluate_assessments(
    body: ClinicalAssessmentRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    use_case: SubmitAssessmentUseCase = Depends(get_submit_assessment_use_case),
    organization_service: OrganizationService = Depends(get_organization_service),
) -> AssessmentsResponse:
    # Validate user role
    if not user.membership or "member" not in user.membership.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    # Map request model to HealthDataDTO
    health_data = HealthDataDTO(
        age=body.age,
        sex=body.sex,
        height=body.height,
        weight=body.weight,
        waist_circumference=body.waist_circumference,
        neck_circumference=body.neck_circumference,
        snoring=body.snoring,
        tired=body.tired,
        observed_apnea=body.observed_apnea,
        hypertension_medication=body.hypertension_medication,
        daily_physical_activity=body.daily_physical_activity,
        fruits_vegetables=body.fruits_vegetables,
        previous_high_glucose=body.previous_high_glucose,
        family_diabetes=body.family_diabetes,
    )

    try:
        results = await use_case.execute(
            user_id=user.id,
            health_data=health_data,
            target_scores=["stop_bang", "findrisc"],
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
            normalized_value=res.normalized_value,
            explanation=res.explanation,
            contributing_factors=res.contributing_factors,
            evaluated_at=getattr(res, "evaluated_at", None)
            or datetime.now(timezone.utc),
        )
        for res in results
    ]

    score_weights = None
    if user.membership and user.membership.organization_id:
        try:
            score_weights = await organization_service.get_score_weights(
                user.membership.organization_id
            )
        except Exception:
            score_weights = None

    return build_assessments_response(
        response_results, page=1, limit=10, score_weights=score_weights
    )


@router.get("", response_model=AssessmentsResponse)
async def get_assessments(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    use_case: GetAssessmentsUseCase = Depends(get_get_assessments_use_case),
    organization_service: OrganizationService = Depends(get_organization_service),
) -> AssessmentsResponse:
    if not user.membership or "member" not in user.membership.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    results = await use_case.execute(user_id=user.id)

    response_results = [
        AssessmentResultResponse(
            score_id=str(res.id),
            score_name=_format_score_display_name(res.score_name),
            risk_level=res.risk_level,
            raw_value=res.raw_value,
            normalized_value=res.normalized_value,
            explanation=res.explanation,
            contributing_factors=res.contributing_factors,
            evaluated_at=res.evaluated_at,
        )
        for res in results
    ]

    score_weights = None
    if user.membership and user.membership.organization_id:
        try:
            score_weights = await organization_service.get_score_weights(
                user.membership.organization_id
            )
        except Exception:
            score_weights = None

    return build_assessments_response(
        response_results, page=page, limit=limit, score_weights=score_weights
    )
