from fastapi import APIRouter, Depends, HTTPException, status

from app.application.dto import AuthenticatedUser
from app.presentation.api.dependencies import (
    get_current_user,
    get_submit_assessment_use_case,
    get_get_assessments_use_case,
)
from app.application.use_cases.assessments.submit_assessment import (
    SubmitAssessmentUseCase,
)
from app.application.use_cases.assessments.get_assessments import GetAssessmentsUseCase
from app.application.dto.risk_scoring import HealthDataDTO
from app.presentation.api.request_models.assessments import ClinicalAssessmentRequest
from app.presentation.api.response_models.assessments import (
    AssessmentsResponse,
    AssessmentResultResponse,
)

router = APIRouter(prefix="/members/me/assessments", tags=["assessments"])


@router.post("/evaluate", response_model=AssessmentsResponse)
async def evaluate_assessments(
    body: ClinicalAssessmentRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    use_case: SubmitAssessmentUseCase = Depends(get_submit_assessment_use_case),
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
            score_name=res.score_name,
            risk_level=res.risk_level,
            raw_value=res.raw_value,
            normalized_value=res.normalized_value,
            explanation=res.explanation,
            contributing_factors=res.contributing_factors,
        )
        for res in results
    ]

    return AssessmentsResponse(results=response_results)


@router.get("", response_model=AssessmentsResponse)
async def get_assessments(
    user: AuthenticatedUser = Depends(get_current_user),
    use_case: GetAssessmentsUseCase = Depends(get_get_assessments_use_case),
) -> AssessmentsResponse:
    if not user.membership or "member" not in user.membership.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    results = await use_case.execute(user_id=user.id)

    response_results = [
        AssessmentResultResponse(
            score_id=str(res.id),
            score_name=res.score_name,
            risk_level=res.risk_level,
            raw_value=res.raw_value,
            normalized_value=res.normalized_value,
            explanation=res.explanation,
            contributing_factors=res.contributing_factors,
        )
        for res in results
    ]

    return AssessmentsResponse(results=response_results)
