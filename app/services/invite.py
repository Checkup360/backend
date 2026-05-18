import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends

from app.core import settings
from app.domain.entities import InviteToken
from app.domain.entities.org_role import OrgRole
from app.repositories.invite import InviteRepository, get_invite_repository
from app.repositories.membership import MembershipRepository, get_membership_repository
from app.repositories.user import UserRepository, get_user_repository


def build_invite_url(token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/invite/{token}"


def build_invite_token(
    *,
    email: str | None,
    expires_in_hours: int,
    max_uses: int,
    organization_id: uuid.UUID | None = None,
    role: OrgRole | None = None,
    is_sysadmin: bool = False,
) -> InviteToken:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
    return InviteToken(
        id=uuid.uuid4(),
        token=token,
        email=email,
        expires_at=expires_at,
        max_uses=max_uses,
        organization_id=organization_id,
        role=role,
        is_sysadmin=is_sysadmin,
    )


class InviteService:
    def __init__(
        self,
        invite_repo: InviteRepository,
        membership_repo: MembershipRepository,
        user_repo: UserRepository,
    ):
        self.invite_repo = invite_repo
        self.membership_repo = membership_repo
        self.user_repo = user_repo

    async def create_invite(
        self,
        *,
        email: str | None,
        expires_in_hours: int,
        max_uses: int,
        organization_id: uuid.UUID | None = None,
        role: OrgRole | None = None,
        is_sysadmin: bool = False,
    ) -> InviteToken:
        invite = build_invite_token(
            email=email,
            expires_in_hours=expires_in_hours,
            max_uses=max_uses,
            organization_id=organization_id,
            role=role,
            is_sysadmin=is_sysadmin,
        )
        return await self.invite_repo.save(invite)

    async def validate_invite(
        self, token: str, email: str
    ) -> tuple[InviteToken | None, str | None]:
        invite, err = await self.invite_repo.fetch_usable_invite(token)
        if err:
            return None, err
        assert invite is not None
        if invite.email and invite.email != email:
            return None, "email_mismatch"
        return invite, None

    async def consume_invite(self, invite_id: uuid.UUID, user_id: uuid.UUID) -> None:
        invite = await self.invite_repo.get(invite_id)
        if invite is None or invite.is_exhausted:
            return

        user = await self.user_repo.get(user_id)
        if user is None:
            return

        if invite.is_sysadmin:
            await self.user_repo.update(user.id, is_superuser=True)
        elif invite.organization_id:
            existing_membership = await self.membership_repo.get_by_user_and_org(
                user.id, invite.organization_id
            )
            if not existing_membership:
                await self.membership_repo.create(
                    user_id=user.id,
                    organization_id=invite.organization_id,
                    role=invite.role or OrgRole.MEMBER,
                )
            else:
                if (
                    invite.role
                    and invite.role == OrgRole.ADMIN
                    and existing_membership.role != OrgRole.ADMIN
                ):
                    await self.membership_repo.update_role(
                        user_id=existing_membership.user_id,
                        organization_id=existing_membership.organization_id,
                        role=invite.role,
                    )
                else:
                    return

        await self.invite_repo.update(invite_id, uses=invite.uses + 1)


async def get_invite_service(
    invite_repo: InviteRepository = Depends(get_invite_repository),
    membership_repo: MembershipRepository = Depends(get_membership_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> InviteService:
    return InviteService(invite_repo, membership_repo, user_repo)
