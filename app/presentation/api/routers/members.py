from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.application.dto import AuthenticatedUser
from app.application.use_cases.assessments.recalculate_member_scores import (
    RecalculateMemberScoresUseCase,
)
from app.application.use_cases.assessments.save_submission import (
    SaveAssessmentSubmissionUseCase,
)
from app.presentation.api.dependencies import (
    get_member_details_service,
    get_member_health_data_service,
    get_recalculate_member_scores_use_case,
    get_save_assessment_submission_use_case,
)
from app.domain.services.time_provider import TimeProvider
from app.domain.services.form_registry import FormRegistry
from app.presentation.api.dependencies import get_time_provider
from app.application.use_cases.members.member_details_service import (
    MemberDetailsService,
)
from app.application.use_cases.members.member_health_data_service import (
    MemberHealthDataService,
)
from app.presentation.api.dependencies import get_current_user
from app.presentation.api.request_models.onboarding import OnboardingRequest
from app.presentation.api.request_models.member_details import MemberProfileUpdate
from app.presentation.api.request_models.member_biometrics import MemberBiometricsUpdate
from app.presentation.api.request_models.member_forms import MemberFormUpdate
from app.presentation.api.response_models import (
    MemberDetailsCreated,
    MemberProfileResponse,
    MemberBiometricsResponse,
)
from app.presentation.api.response_models.member_forms import (
    EvaluatedScoreSummary,
    MemberFormResponse,
    MemberFormSubmissionResponse,
)

router = APIRouter(prefix="/members", tags=["members"])


@router.post("/me/details", response_model=MemberDetailsCreated)
async def create_my_member_details(
    body: OnboardingRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    details_service: MemberDetailsService = Depends(get_member_details_service),
    health_data_service: MemberHealthDataService = Depends(
        get_member_health_data_service
    ),
) -> MemberDetailsCreated:
    if not details_service.is_member_user(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    try:
        await details_service.complete_onboarding(
            user,
            body.date_of_birth,
            first_name=body.first_name,
            last_name=body.last_name,
            phone_number=body.phone_number,
            avatar_url=body.avatar_url,
        )

        await health_data_service.update_health_data(
            user_id=user.id,
            biological_sex=body.biological_sex,
            height=body.height,
            weight=body.weight,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return MemberDetailsCreated()


@router.get("/me/profile", response_model=MemberProfileResponse)
async def get_my_profile(
    user: AuthenticatedUser = Depends(get_current_user),
    details_service: MemberDetailsService = Depends(get_member_details_service),
) -> MemberProfileResponse:
    profile = await details_service.get_profile(user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="profile_not_found",
        )
    priority_topics = details_service.get_priority_topics(profile)
    return MemberProfileResponse(
        first_name=profile.first_name,
        last_name=profile.last_name,
        phone_number=profile.phone_number,
        date_of_birth=profile.date_of_birth,
        avatar_url=profile.avatar_url,
        priority_topics=priority_topics,
    )


@router.patch("/me/profile", response_model=MemberProfileResponse)
async def update_my_profile(
    body: MemberProfileUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    details_service: MemberDetailsService = Depends(get_member_details_service),
) -> MemberProfileResponse:
    try:
        updated = await details_service.update_profile(
            user_id=user.id,
            first_name=body.first_name,
            last_name=body.last_name,
            phone_number=body.phone_number,
            date_of_birth=body.date_of_birth,
            avatar_url=body.avatar_url,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    priority_topics = details_service.get_priority_topics(updated)
    return MemberProfileResponse(
        first_name=updated.first_name,
        last_name=updated.last_name,
        phone_number=updated.phone_number,
        date_of_birth=updated.date_of_birth,
        avatar_url=updated.avatar_url,
        priority_topics=priority_topics,
    )


@router.get("/me/biometrics", response_model=MemberBiometricsResponse)
async def get_my_biometrics(
    user: AuthenticatedUser = Depends(get_current_user),
    health_data_service: MemberHealthDataService = Depends(
        get_member_health_data_service
    ),
) -> MemberBiometricsResponse:
    biometrics = await health_data_service.get_health_data(user.id)
    if biometrics is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="biometrics_not_found",
        )
    return MemberBiometricsResponse(
        biological_sex=biometrics.biological_sex,
        height=biometrics.height,
        weight=biometrics.weight,
        waist_circumference=biometrics.waist_circumference,
        neck_circumference=biometrics.neck_circumference,
    )


@router.patch("/me/biometrics", response_model=MemberBiometricsResponse)
async def update_my_biometrics(
    body: MemberBiometricsUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    health_data_service: MemberHealthDataService = Depends(
        get_member_health_data_service
    ),
) -> MemberBiometricsResponse:
    await health_data_service.update_health_data(
        user_id=user.id,
        biological_sex=body.biological_sex,
        height=body.height,
        weight=body.weight,
    )

    biometrics = await health_data_service.get_health_data(user.id)
    if not biometrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="biometrics_not_found",
        )

    return MemberBiometricsResponse(
        biological_sex=biometrics.biological_sex,
        height=biometrics.height,
        weight=biometrics.weight,
        waist_circumference=biometrics.waist_circumference,
        neck_circumference=biometrics.neck_circumference,
    )


FORM_FIELDS_MAP: dict[str, list[str]] = FormRegistry().get_form_fields_map()


@router.get("/me/forms/{form_type}", response_model=MemberFormResponse)
async def get_my_form_data(
    form_type: str,
    user: AuthenticatedUser = Depends(get_current_user),
    health_data_service: MemberHealthDataService = Depends(
        get_member_health_data_service
    ),
) -> MemberFormResponse:
    if form_type not in FORM_FIELDS_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported form type '{form_type}'",
        )

    allowed_fields = FORM_FIELDS_MAP[form_type]
    health_data = await health_data_service.get_health_data(user.id)
    data: dict[str, Any] = {}
    if health_data:
        for field in allowed_fields:
            val = getattr(health_data, field, None)
            if val is not None:
                data[field] = val

    return MemberFormResponse(form_type=form_type, data=data)


@router.put("/me/forms/{form_type}", response_model=MemberFormSubmissionResponse)
async def update_my_form_data(
    form_type: str,
    body: MemberFormUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    health_data_service: MemberHealthDataService = Depends(
        get_member_health_data_service
    ),
    recalculate_use_case: RecalculateMemberScoresUseCase = Depends(
        get_recalculate_member_scores_use_case
    ),
    save_submission_use_case: SaveAssessmentSubmissionUseCase = Depends(
        get_save_assessment_submission_use_case
    ),
    time_provider: TimeProvider = Depends(get_time_provider),
) -> MemberFormSubmissionResponse:
    if form_type not in FORM_FIELDS_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported form type '{form_type}'",
        )

    allowed_fields = FORM_FIELDS_MAP[form_type]
    submitted_dict = body.model_dump(exclude_unset=True)
    update_kwargs = {
        k: v for k, v in submitted_dict.items() if k in allowed_fields and v is not None
    }

    if update_kwargs:
        await health_data_service.update_health_data(user.id, **update_kwargs)

    submission_id = None
    if user.membership:
        submission = await save_submission_use_case.execute(
            user_id=user.id,
            organization_id=user.membership.organization_id,
            form_type=form_type,
            answers=update_kwargs,
            submitted_at=time_provider.utcnow(),
        )
        submission_id = submission.id

    updated_keys = list(update_kwargs.keys())
    newly_evaluated = await recalculate_use_case.execute(
        user_id=user.id,
        updated_fields=updated_keys,
        submission_id=submission_id,
    )

    recalculated_summaries = [
        EvaluatedScoreSummary(
            score_name=s.score_name,
            risk_level=s.risk_level,
            raw_value=s.raw_value,
            explanation=s.explanation,
            attention_flags=s.attention_flags,
        )
        for s in newly_evaluated
    ]

    return MemberFormSubmissionResponse(
        form_type=form_type,
        status="success",
        updated_fields=updated_keys,
        recalculated_scores=recalculated_summaries,
    )
