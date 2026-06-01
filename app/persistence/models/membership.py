import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, ForeignKey, Enum, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.database import Base
from app.domain.entities.org_role import OrgRole
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.persistence.models.department import Department
    from app.persistence.models.organization import Organization
    from app.persistence.models.user import User


class Membership(Base):
    __tablename__ = "memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id"), primary_key=True, unique=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), primary_key=True
    )
    roles: Mapped[list[OrgRole]] = mapped_column(
        ARRAY(Enum(OrgRole, name="orgrole", create_type=False)),
        default=[OrgRole.MEMBER],
        nullable=False,
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="memberships",
        lazy="joined",
        overlaps="department,memberships",
    )
    user: Mapped["User"] = relationship("User", back_populates="membership")
    department: Mapped["Department | None"] = relationship(
        "Department",
        back_populates="memberships",
        lazy="joined",
        overlaps="organization,memberships",
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["department_id", "organization_id"],
            ["departments.id", "departments.organization_id"],
            name="fk_memberships_department_org",
        ),
        Index("ix_user_org_organization_id", "organization_id"),
    )
