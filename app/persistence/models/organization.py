import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.database import Base
from app.persistence.models.department import Department
from app.persistence.models.membership import Membership


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
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
