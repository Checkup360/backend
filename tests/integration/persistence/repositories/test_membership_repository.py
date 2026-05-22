import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.repositories.membership import MembershipRepository
from app.domain.entities.org_role import OrgRole
from app.persistence.models.organization import Organization
from app.persistence.models.user import User


@pytest.mark.asyncio
async def test_get_by_user_and_org(db: AsyncSession):
    repo = MembershipRepository(db)

    # Setup: need org and user
    org = Organization(id=uuid.uuid4(), name="Org", slug="org")
    user = User(id=uuid.uuid4(), email="user@test.com", hashed_password="pw")
    db.add_all([org, user])
    await db.flush()

    await repo.create(user_id=user.id, organization_id=org.id, role=OrgRole.ADMIN)

    found = await repo.get_by_user_and_org(user.id, org.id)
    assert found is not None
    assert OrgRole.ADMIN in found.roles

    assert await repo.get_by_user_and_org(uuid.uuid4(), org.id) is None
