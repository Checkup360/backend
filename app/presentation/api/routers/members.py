from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.application.dto import AuthenticatedUser
from app.application.use_cases.assessments.recalculate_member_scores import (
    RecalculateMemberScoresUseCase,
)
from app.presentation.api.dependencies import (
    get_member_details_service,
    get_member_biometrics_service,
    get_recalculate_member_scores_use_case,
)
from app.application.use_cases.members.member_details_service import (
    MemberDetailsService,
)
from app.application.use_cases.members.member_biometrics_service import (
    MemberBiometricsService,
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
    biometrics_service: MemberBiometricsService = Depends(
        get_member_biometrics_service
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
        )

        await biometrics_service.update_biometrics(
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
        priority_topics=priority_topics,
    )


@router.get("/me/biometrics", response_model=MemberBiometricsResponse)
async def get_my_biometrics(
    user: AuthenticatedUser = Depends(get_current_user),
    biometrics_service: MemberBiometricsService = Depends(
        get_member_biometrics_service
    ),
) -> MemberBiometricsResponse:
    biometrics = await biometrics_service.get_biometrics(user.id)
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
    biometrics_service: MemberBiometricsService = Depends(
        get_member_biometrics_service
    ),
) -> MemberBiometricsResponse:
    # First, verify the user has an established profile before saving biometrics
    # (they should have gone through onboarding). If not, we could return 404.
    # We rely on the service to just update or insert.
    await biometrics_service.update_biometrics(
        user_id=user.id,
        biological_sex=body.biological_sex,
        height=body.height,
        weight=body.weight,
    )

    biometrics = await biometrics_service.get_biometrics(user.id)
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


FORM_FIELDS_MAP: dict[str, list[str]] = {
    "biometrics": [
        "biological_sex",
        "height",
        "weight",
        "waist_circumference",
        "neck_circumference",
    ],
    "sleep": ["snoring", "tired", "observed_apnea", "neck_circumference"],
    "habits": [
        "daily_physical_activity",
        "fruits_vegetables",
        "hypertension_medication",
        "previous_high_glucose",
        "family_diabetes",
    ],
}


@router.get("/me/forms/{form_type}", response_model=MemberFormResponse)
async def get_my_form_data(
    form_type: str,
    user: AuthenticatedUser = Depends(get_current_user),
    biometrics_service: MemberBiometricsService = Depends(
        get_member_biometrics_service
    ),
) -> MemberFormResponse:
    if form_type not in FORM_FIELDS_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported form type '{form_type}'",
        )

    allowed_fields = FORM_FIELDS_MAP[form_type]
    biometrics = await biometrics_service.get_biometrics(user.id)
    data: dict[str, Any] = {}
    if biometrics:
        for field in allowed_fields:
            val = getattr(biometrics, field, None)
            if val is not None:
                data[field] = val

    return MemberFormResponse(form_type=form_type, data=data)


@router.put("/me/forms/{form_type}", response_model=MemberFormSubmissionResponse)
async def update_my_form_data(
    form_type: str,
    body: MemberFormUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    biometrics_service: MemberBiometricsService = Depends(
        get_member_biometrics_service
    ),
    recalculate_use_case: RecalculateMemberScoresUseCase = Depends(
        get_recalculate_member_scores_use_case
    ),
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
        await biometrics_service.update_biometrics(user.id, **update_kwargs)

    updated_keys = list(update_kwargs.keys())
    newly_evaluated = await recalculate_use_case.execute(
        user_id=user.id, updated_fields=updated_keys
    )

    recalculated_summaries = [
        EvaluatedScoreSummary(
            score_name=s.score_name,
            risk_level=s.risk_level,
            raw_value=s.raw_value,
            explanation=s.explanation,
        )
        for s in newly_evaluated
    ]

    return MemberFormSubmissionResponse(
        form_type=form_type,
        status="success",
        updated_fields=updated_keys,
        recalculated_scores=recalculated_summaries,
    )
