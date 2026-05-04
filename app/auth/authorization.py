import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.users import current_active_user
from app.database import get_db
from app.models import Membership, Organization, User
from app.models.membership import OrgRole


def require_superuser(
    current_user: User = Depends(current_active_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return current_user


async def require_organization_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
) -> Membership:
    body = await request.json()
    organization_id = body.get("organization_id")
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="organization_id_required",
        )

    try:
        organization_uuid = uuid.UUID(organization_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid_organization_id",
        )

    organization = await db.get(Organization, organization_uuid)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="organization_not_found",
        )

    membership = await db.scalar(
        select(Membership).where(
            (Membership.user_id == current_user.id)
            & (Membership.organization_id == organization_uuid)
        )
    )
    if not membership or membership.role != OrgRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    return membership
