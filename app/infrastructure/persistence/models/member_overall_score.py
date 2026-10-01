from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base


class MemberOverallScoreModel(Base):
    __tablename__ = "member_overall_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score_weights_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organization_score_weights.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_submissions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    overall_health_index: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(100), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    user = relationship("User", backref="overall_scores")
    organization = relationship("Organization", backref="member_overall_scores")
    score_weights = relationship(
        "OrganizationScoreWeightsModel", backref="member_overall_scores"
    )
    submission = relationship(
        "AssessmentSubmissionModel", backref="overall_score_records"
    )

    __table_args__ = (
        Index(
            "idx_member_overall_scores_user_evaluated",
            "user_id",
            "evaluated_at",
        ),
        Index(
            "idx_member_overall_scores_org_evaluated",
            "organization_id",
            "evaluated_at",
        ),
    )
