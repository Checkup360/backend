import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.infrastructure.persistence.database import Base


class RiskScoreModel(Base):
    __tablename__ = "risk_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score_name = Column(String(100), nullable=False)
    risk_level = Column(String(100), nullable=True)
    raw_value = Column(Float, nullable=True)
    normalized_value = Column(Float, nullable=True)
    explanation = Column(String, nullable=True)
    contributing_factors = Column(JSON, nullable=False, default=dict)
    evaluated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="risk_scores")
