import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base
from app.domain.value_objects.org_role import OrgRole
from app.infrastructure.persistence.models.department import Department
from app.infrastructure.persistence.models.organization import Organization


class InviteToken(Base):
    __tablename__ = "invite_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)

    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    uses: Mapped[int] = mapped_column(Integer, default=0)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    role: Mapped[OrgRole | None] = mapped_column(Enum(OrgRole), nullable=True)

    is_sysadmin: Mapped[bool] = mapped_column(Boolean, default=False)

    organization: Mapped[Organization | None] = relationship(
        "Organization", backref="invite_tokens"
    )
    department: Mapped[Department | None] = relationship(
        "Department", overlaps="invite_tokens,organization"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["department_id", "organization_id"],
            ["departments.id", "departments.organization_id"],
            name="fk_invite_tokens_department_org",
        ),
    )

    @property
    def is_exhausted(self) -> bool:
        return self.uses >= self.max_uses
