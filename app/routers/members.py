from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.machinery.users import current_active_user
from app.dependencies import get_member_details_service
from app.domain.services.member_details import MemberDetailsService
from app.persistence.models import User
from app.schemas.member_details import MemberDetailsCreate, MemberDetailsCreated

router = APIRouter(prefix="/members", tags=["members"])


@router.post("/me/details", response_model=MemberDetailsCreated)
async def create_my_member_details(
    body: MemberDetailsCreate,
    user: User = Depends(current_active_user),
    service: MemberDetailsService = Depends(get_member_details_service),
) -> MemberDetailsCreated:
    if not service.is_member_only_user(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    try:
        await service.complete_onboarding(user, body.date_of_birth)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )

    return MemberDetailsCreated()
