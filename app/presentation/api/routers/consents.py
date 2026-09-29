import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.application.dto import AuthenticatedUser
from app.application.use_cases.consents import (
    AcceptConsentUseCase,
    GetActiveConsentsUseCase,
    RevokeConsentUseCase,
)
from app.domain.exceptions import (
    CannotRevokeFundamentalConsentError,
    ConsentAlreadyRevokedError,
    ConsentNotFoundError,
    FormTypeRequiredError,
    InvalidConsentTypeError,
    InvalidFormTypeError,
)
from app.presentation.api.dependencies import (
    get_accept_consent_use_case,
    get_active_consents_use_case,
    get_current_user,
    get_revoke_consent_use_case,
)
from app.presentation.api.request_models.consents import AcceptConsentRequest
from app.presentation.api.response_models.consents import (
    ActiveConsentsResponse,
    UserConsentResponse,
)

router = APIRouter(prefix="/consents", tags=["Consents"])


def _extract_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get(
    "/current",
    response_model=ActiveConsentsResponse,
    summary="Get active consents for current user",
)
async def get_current_user_consents(
    current_user: AuthenticatedUser = Depends(get_current_user),
    use_case: GetActiveConsentsUseCase = Depends(get_active_consents_use_case),
) -> ActiveConsentsResponse:
    active_consents = await use_case.execute(user_id=current_user.id)
    return ActiveConsentsResponse(
        terms_and_conditions=UserConsentResponse.model_validate(
            active_consents.terms_and_conditions
        )
        if active_consents.terms_and_conditions
        else None,
        privacy_policy=UserConsentResponse.model_validate(
            active_consents.privacy_policy
        )
        if active_consents.privacy_policy
        else None,
        health_data_processing=UserConsentResponse.model_validate(
            active_consents.health_data_processing
        )
        if active_consents.health_data_processing
        else None,
        form_consents={
            k: UserConsentResponse.model_validate(v)
            for k, v in active_consents.form_consents.items()
        },
    )


@router.post(
    "",
    response_model=UserConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record acceptance of a consent",
)
async def accept_consent(
    body: AcceptConsentRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    use_case: AcceptConsentUseCase = Depends(get_accept_consent_use_case),
) -> UserConsentResponse:
    ip_address = _extract_ip(request)
    user_agent = request.headers.get("user-agent")

    try:
        consent = await use_case.execute(
            user_id=current_user.id,
            consent_type=body.consent_type,
            form_type=body.form_type,
            document_version=body.document_version,
            document_hash=body.document_hash,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return UserConsentResponse.model_validate(consent)
    except FormTypeRequiredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Form type is required for FORM_CONSENT",
        )
    except InvalidFormTypeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid form type",
        )
    except InvalidConsentTypeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid consent type",
        )


@router.post(
    "/{consent_id}/revoke",
    response_model=UserConsentResponse,
    summary="Revoke a consent",
)
async def revoke_consent(
    consent_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    use_case: RevokeConsentUseCase = Depends(get_revoke_consent_use_case),
) -> UserConsentResponse:
    try:
        revoked = await use_case.execute(
            user_id=current_user.id,
            consent_id=consent_id,
        )
        return UserConsentResponse.model_validate(revoked)
    except ConsentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found",
        )
    except ConsentAlreadyRevokedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Consent has already been revoked",
        )
    except CannotRevokeFundamentalConsentError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fundamental platform terms and privacy policy cannot be revoked independently",
        )
