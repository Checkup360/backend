import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.department import Department
from app.infrastructure.persistence.models.membership import Membership


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    score_weights: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    memberships: Mapped[list["Membership"]] = relationship(
        "Membership",
        back_populates="organization",
        overlaps="department,memberships",
    )
    departments: Mapped[list["Department"]] = relationship(
        "Department", back_populates="organization"
    )
