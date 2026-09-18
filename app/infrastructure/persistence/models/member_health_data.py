import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.user import User


class MemberHealthData(Base):
    __tablename__ = "member_health_data"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), primary_key=True)
    biological_sex: Mapped[str | None] = mapped_column(String, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    waist_circumference: Mapped[float | None] = mapped_column(Float, nullable=True)
    triglycerides: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cholesterol: Mapped[float | None] = mapped_column(Float, nullable=True)
    hdl_cholesterol: Mapped[float | None] = mapped_column(Float, nullable=True)
    systolic_blood_pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    diastolic_blood_pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    fasting_glucose: Mapped[float | None] = mapped_column(Float, nullable=True)
    glucose_lowering_medication: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    statins: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    lab_study_date: Mapped[str | None] = mapped_column(String, nullable=True)
    neck_circumference: Mapped[float | None] = mapped_column(Float, nullable=True)
    snoring: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    tired: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    observed_apnea: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    smoker: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    hypertension_medication: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    daily_physical_activity: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fruits_vegetables: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    previous_high_glucose: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    family_diabetes: Mapped[str | None] = mapped_column(String, nullable=True)
    little_interest: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feeling_down: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_trouble: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tired_energy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    appetite: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feeling_bad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    concentration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    psychomotor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    self_harm_thoughts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eoss_physical_health_stage: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    eoss_mental_health_stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eoss_functional_stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nordic_nmq_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    audit_c_frequency: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audit_c_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audit_c_heavy_drinking: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pss10_q1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pss10_q2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pss10_q3: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pss10_q4: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pss10_q5: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pss10_q6: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pss10_q7: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pss10_q8: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pss10_q9: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pss10_q10: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User", back_populates="member_health_data")
