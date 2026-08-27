import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.user import User


class MemberBiometrics(Base):
    __tablename__ = "member_biometrics"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), primary_key=True)
    biological_sex: Mapped[str | None] = mapped_column(String, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    waist_circumference: Mapped[float | None] = mapped_column(Float, nullable=True)
    neck_circumference: Mapped[float | None] = mapped_column(Float, nullable=True)
    snoring: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    tired: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    observed_apnea: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    hypertension_medication: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    daily_physical_activity: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fruits_vegetables: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    previous_high_glucose: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    family_diabetes: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User", back_populates="member_biometrics")
