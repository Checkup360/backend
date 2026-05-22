import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, ForeignKey, JSON, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.database import Base
from app.domain.entities.org_role import OrgRole
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.persistence.models.organization import Organization
    from app.persistence.models.user import User


class OrgRoleArray(TypeDecorator):
    """Custom type for storing array of OrgRole as JSON in both SQLite and PostgreSQL."""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return [role.value if isinstance(role, OrgRole) else role for role in value]

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return [OrgRole(role) for role in value]


class Membership(Base):
    __tablename__ = "memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), primary_key=True
    )
    roles: Mapped[list[OrgRole]] = mapped_column(
        OrgRoleArray,
        default=[OrgRole.MEMBER],
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="memberships", lazy="joined"
    )
    user: Mapped["User"] = relationship("User", back_populates="memberships")
    __table_args__ = (Index("ix_user_org_organization_id", "organization_id"),)
