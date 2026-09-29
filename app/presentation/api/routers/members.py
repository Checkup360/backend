from typing import Any
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.application.dto import AuthenticatedUser
from app.application.use_cases.assessments.recalculate_member_scores import (
    RecalculateMemberScoresUseCase,
)
from app.application.use_cases.assessments.save_submission import (
    SaveAssessmentSubmissionUseCase,
)
from app.application.use_cases.members.delete_member_avatar import (
    DeleteMemberAvatarUseCase,
)
from app.application.use_cases.members.export_member_data import (
    ExportMemberDataUseCase,
)
from app.application.use_cases.members.get_member_risk_priorities import (
    GetMemberRiskPrioritiesUseCase,
)
from app.application.use_cases.members.upload_member_avatar import (
    UploadMemberAvatarUseCase,
)
from app.application.use_cases.assessments.get_active_member_forms import (
    GetActiveMemberFormsUseCase,
)
from app.presentation.api.dependencies import (
    get_delete_member_avatar_use_case,
    get_export_member_data_use_case,
    get_get_active_member_forms_use_case,
    get_member_details_service,
    get_member_health_data_service,
    get_member_risk_priorities_use_case,
    get_recalculate_member_scores_use_case,
    get_save_assessment_submission_use_case,
    get_upload_member_avatar_use_case,
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
from app.domain.entities.user_consent import UserConsent
from app.presentation.api.authorization import (
    require_biometrics_consent,
    require_form_consent,
    require_member_role,
)
from app.presentation.api.dependencies import get_current_user
from app.presentation.api.request_models.onboarding import OnboardingRequest
from app.presentation.api.request_models.member_details import MemberProfileUpdate
from app.presentation.api.request_models.member_biometrics import MemberBiometricsUpdate
from app.presentation.api.request_models.member_forms import MemberFormUpdate
from app.presentation.api.response_models import (
    AvatarUploadResponse,
    MemberDataExportResponse,
    MemberDetailsCreated,
    MemberProfileResponse,
    MemberBiometricsResponse,
    UserConsentResponse,
)
from app.presentation.api.response_models.member_details import (
    MemberRiskPrioritiesResponse,
)
from app.presentation.api.response_models.member_forms import (
    ActiveFormDefinitionResponse,
    ActiveFormsResponse,
    EvaluatedScoreSummary,
    MemberFormResponse,
    MemberFormSubmissionResponse,
)

router = APIRouter(
    prefix="/members",
    tags=["members"],
    dependencies=[Depends(require_member_role)],
)


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


@router.post("/me/avatar", response_model=AvatarUploadResponse)
async def upload_my_avatar(
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_user),
    use_case: UploadMemberAvatarUseCase = Depends(get_upload_member_avatar_use_case),
) -> AvatarUploadResponse:
    content = await file.read()
    try:
        avatar_url = await use_case.execute(
            user_id=user.id,
            content=content,
            filename=file.filename or "avatar.png",
            content_type=file.content_type or "image/png",
        )
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "member_details_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_msg,
        )
    return AvatarUploadResponse(avatar_url=avatar_url)


@router.delete("/me/avatar", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_avatar(
    user: AuthenticatedUser = Depends(get_current_user),
    use_case: DeleteMemberAvatarUseCase = Depends(get_delete_member_avatar_use_case),
) -> None:
    try:
        await use_case.execute(user_id=user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/me/risk-priorities", response_model=MemberRiskPrioritiesResponse)
async def get_my_risk_priorities(
    user: AuthenticatedUser = Depends(get_current_user),
    use_case: GetMemberRiskPrioritiesUseCase = Depends(
        get_member_risk_priorities_use_case
    ),
) -> MemberRiskPrioritiesResponse:
    org_id = user.membership.organization_id if user.membership else None
    dto = await use_case.execute(user_id=user.id, organization_id=org_id)
    return MemberRiskPrioritiesResponse(
        user_id=dto.user_id,
        risk_weights=dto.risk_weights,
        highest_risk=dto.highest_risk,
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
    _consent: UserConsent = Depends(require_biometrics_consent),
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


@router.get("/me/forms/active", response_model=ActiveFormsResponse)
async def get_my_active_forms(
    user: AuthenticatedUser = Depends(get_current_user),
    use_case: GetActiveMemberFormsUseCase = Depends(
        get_get_active_member_forms_use_case
    ),
    health_data_service: MemberHealthDataService = Depends(
        get_member_health_data_service
    ),
) -> ActiveFormsResponse:
    org_id = user.membership.organization_id if user.membership else None
    active_defs = await use_case.execute(organization_id=org_id)
    health_data = await health_data_service.get_health_data(user.id)

    response_items = []
    for f in active_defs:
        is_completed = False
        if health_data:
            is_completed = True
            for field in f.fields:
                val = getattr(health_data, field, None)
                if val is None or (isinstance(val, dict) and not val):
                    is_completed = False
                    break
        response_items.append(
            ActiveFormDefinitionResponse(
                form_type=f.form_type,
                fields=f.fields,
                is_completed=is_completed,
            )
        )
    return ActiveFormsResponse(active_forms=response_items)


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
    form_consent: UserConsent = Depends(require_form_consent),
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
            consent_id=form_consent.id,
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


def _extract_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get(
    "/me/export",
    response_model=MemberDataExportResponse,
    summary="Export all member personal and health data (Habeas Data / Ley 25.326)",
)
async def export_my_member_data(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    use_case: ExportMemberDataUseCase = Depends(get_export_member_data_use_case),
) -> MemberDataExportResponse:
    ip_address = _extract_ip(request)
    user_agent = request.headers.get("user-agent")

    export_dto = await use_case.execute(
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return MemberDataExportResponse(
        user_id=export_dto.user_id,
        email=export_dto.email,
        first_name=export_dto.first_name,
        last_name=export_dto.last_name,
        phone_number=export_dto.phone_number,
        date_of_birth=export_dto.date_of_birth,
        avatar_url=export_dto.avatar_url,
        organization_id=export_dto.organization_id,
        organization_name=export_dto.organization_name,
        roles=export_dto.roles,
        consents=[
            UserConsentResponse(
                id=c.id,
                user_id=c.user_id,
                consent_type=c.consent_type,
                form_type=c.form_type,
                document_version=c.document_version,
                document_hash=c.document_hash,
                accepted_at=c.accepted_at,
                revoked_at=c.revoked_at,
            )
            for c in export_dto.consents
        ],
        health_data=export_dto.health_data,
        assessment_submissions=export_dto.assessment_submissions,
        risk_scores=export_dto.risk_scores,
        exported_at=export_dto.exported_at,
        compliance_notice=export_dto.compliance_notice,
    )
