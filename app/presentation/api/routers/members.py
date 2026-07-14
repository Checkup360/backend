from fastapi import APIRouter, Depends, HTTPException, status

from app.application.dto import AuthenticatedUser
from app.presentation.api.dependencies import get_member_details_service
from app.application.use_cases.members.member_details_service import (
    MemberDetailsService,
)
from app.presentation.api.dependencies import get_current_user
from app.presentation.api.request_models import MemberDetailsCreate
from app.presentation.api.response_models import MemberDetailsCreated

router = APIRouter(prefix="/members", tags=["members"])


@router.post("/me/details", response_model=MemberDetailsCreated)
async def create_my_member_details(
    body: MemberDetailsCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    service: MemberDetailsService = Depends(get_member_details_service),
) -> MemberDetailsCreated:
    if not service.is_member_user(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    try:
        await service.complete_onboarding(user, body.date_of_birth)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )

    return MemberDetailsCreated()
