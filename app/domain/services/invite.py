import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app.domain.entities import InviteToken, Membership
from app.domain.value_objects import OrgRole
from app.domain.exceptions import (
    InviteDepartmentNotFoundError,
    InviteEmailMismatchError,
    InviteExhaustedError,
    InviteExpiredError,
    InviteNotFoundError,
    UserNotFoundError,
)
from app.domain.repositories import (
    DepartmentRepository,
    InviteRepository,
    MembershipRepository,
    UserRepository,
)


def build_invite_token(
    *,
    email: str | None,
    expires_in_hours: int,
    max_uses: int,
    organization_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
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
        department_id=department_id,
        role=role,
        is_sysadmin=is_sysadmin,
    )


class InviteService:
    def __init__(
        self,
        invite_repo: InviteRepository,
        membership_repo: MembershipRepository,
        user_repo: UserRepository,
        department_repo: DepartmentRepository | None = None,
    ):
        self.invite_repo = invite_repo
        self.membership_repo = membership_repo
        self.user_repo = user_repo
        self.department_repo = department_repo

    async def create_invite(
        self,
        *,
        email: str | None,
        expires_in_hours: int,
        max_uses: int,
        organization_id: uuid.UUID | None = None,
        department_id: uuid.UUID | None = None,
        role: OrgRole | None = None,
        is_sysadmin: bool = False,
    ) -> InviteToken:
        if department_id is not None and self.department_repo is not None:
            if organization_id is None:
                raise InviteDepartmentNotFoundError()
            department = await self.department_repo.get_by_organization(
                organization_id, department_id
            )
            if not department:
                raise InviteDepartmentNotFoundError()

        invite = build_invite_token(
            email=email,
            expires_in_hours=expires_in_hours,
            max_uses=max_uses,
            organization_id=organization_id,
            department_id=department_id,
            role=role,
            is_sysadmin=is_sysadmin,
        )
        return await self.invite_repo.save(invite)

    async def _check_usable(self, token: str) -> InviteToken:
        invite = await self.invite_repo.get_by_token(token)
        if not invite:
            raise InviteNotFoundError()
        if invite.is_exhausted:
            raise InviteExhaustedError()
        expires_at = invite.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise InviteExpiredError()
        return invite

    async def check_invite_usable(self, token: str) -> InviteToken:
        return await self._check_usable(token)

    async def validate_invite(self, token: str, email: str) -> InviteToken:
        invite = await self._check_usable(token)
        if invite.email and invite.email != email:
            raise InviteEmailMismatchError()
        return invite

    async def consume_invite(self, invite_id: uuid.UUID, user_id: uuid.UUID) -> None:
        invite = await self.invite_repo.get(invite_id)
        if invite is None:
            raise InviteNotFoundError()
        if invite.is_exhausted:
            raise InviteExhaustedError()

        user = await self.user_repo.get(user_id)
        if user is None:
            raise UserNotFoundError()

        if invite.is_sysadmin:
            await self.user_repo.update(user.id, is_superuser=True)
        elif invite.organization_id:
            existing_membership = await self.membership_repo.get_by_user_and_org(
                user.id, invite.organization_id
            )

            # Ensure we have an OrgRole enum
            invite_role = invite.role or OrgRole.MEMBER
            if isinstance(invite_role, str):
                invite_role = OrgRole(invite_role)

            if not existing_membership:
                membership = Membership(
                    user_id=user.id,
                    organization_id=invite.organization_id,
                    roles=[invite_role],
                    department_id=invite.department_id,
                )
            else:
                # Add role to existing membership if not already present
                if invite_role not in existing_membership.roles:
                    existing_membership.roles = existing_membership.roles + [
                        invite_role
                    ]
                membership = existing_membership
                if invite.department_id is not None:
                    membership.department_id = invite.department_id

            await self.membership_repo.save(membership)
        await self.invite_repo.update(invite_id, uses=invite.uses + 1)
