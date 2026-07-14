from fastapi_users.db import (
    SQLAlchemyBaseOAuthAccountTableUUID,
    SQLAlchemyBaseUserTableUUID,
)
from sqlalchemy.orm import Mapped, relationship

from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models.member_details import MemberDetails
from app.infrastructure.persistence.models.membership import Membership


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined"
    )
    membership: Mapped["Membership | None"] = relationship(
        "Membership", back_populates="user", lazy="joined", uselist=False
    )
    member_details: Mapped["MemberDetails | None"] = relationship(
        "MemberDetails", back_populates="user", lazy="joined", uselist=False
    )
