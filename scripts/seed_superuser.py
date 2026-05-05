import os
import sys
import uuid

from fastapi_users.password import PasswordHelper
from sqlalchemy import select

from app.database import async_session_maker
from app.models import Membership, Organization, User
from app.models.membership import OrgRole

_password_helper = PasswordHelper()


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"[seed] missing required env var: {name}", file=sys.stderr)
        sys.exit(2)
    return value


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


async def _ensure_superuser(email: str, password: str, overwrite: bool) -> User:
    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.email == email))

        if user is None:
            user = User(
                email=email,
                hashed_password=_password_helper.hash(password),
                is_active=True,
                is_verified=True,
                is_superuser=True,
            )
            session.add(user)
        elif overwrite:
            user.hashed_password = _password_helper.hash(password)
            user.is_active = True
            user.is_verified = True
            user.is_superuser = True

        await session.commit()
        await session.refresh(user)
        return user


async def _ensure_org_admin_membership(
    user_id: uuid.UUID, slug: str, name: str
) -> None:
    async with async_session_maker() as session:
        org = await session.scalar(
            select(Organization).where(Organization.slug == slug)
        )
        if org is None:
            org = Organization(name=name, slug=slug)
            session.add(org)
            await session.flush()

        membership = await session.scalar(
            select(Membership).where(
                (Membership.user_id == user_id) & (Membership.organization_id == org.id)
            )
        )
        if membership is None:
            session.add(
                Membership(user_id=user_id, organization_id=org.id, role=OrgRole.ADMIN)
            )
        else:
            membership.role = OrgRole.ADMIN

        await session.commit()


async def main() -> None:
    email = _required_env("SUPERUSER_EMAIL")
    password = _required_env("SUPERUSER_PASSWORD")
    overwrite = _truthy(os.getenv("SEED_OVERWRITE"))

    user = await _ensure_superuser(email, password, overwrite=overwrite)

    org_slug = os.getenv("SEED_ORG_SLUG")
    if org_slug:
        org_name = os.getenv("SEED_ORG_NAME") or org_slug
        await _ensure_org_admin_membership(user.id, org_slug, org_name)
        print(
            f"[seed] superuser={email} org={org_slug} "
            f"(overwrite={overwrite}, admin membership ensured)"
        )
    else:
        print(f"[seed] superuser={email} (overwrite={overwrite})")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
