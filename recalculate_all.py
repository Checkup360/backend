import asyncio
import httpx
from app.infrastructure.persistence.database import async_session_maker
from app.infrastructure.persistence.models.user import User
from sqlalchemy import select, delete
from app.infrastructure.persistence.models.risk_score import RiskScoreModel
from app.infrastructure.persistence.repositories.member_health_data import (
    SQLAlchemyMemberHealthDataRepository,
)
from app.infrastructure.persistence.repositories.member_details import (
    MemberDetailsRepository,
)
from app.infrastructure.persistence.repositories.risk_score import (
    SQLAlchemyRiskScoreRepository,
)
from app.infrastructure.external.engine_api_adapter import HttpEngineScoringAdapter
from app.infrastructure.config import settings
from app.application.use_cases.assessments.recalculate_member_scores import (
    RecalculateMemberScoresUseCase,
)


async def main():
    async with httpx.AsyncClient() as client:
        async with async_session_maker() as session:
            # 1. Delete all audit_c and pss10 scores so they get regenerated
            await session.execute(
                delete(RiskScoreModel).where(
                    RiskScoreModel.score_name.in_(
                        ["AUDIT-C Alcohol Risk", "PSS-10 Perceived Stress Scale"]
                    )
                )
            )
            await session.commit()
            print("Deleted old scores")

            # 2. Get all users
            result = await session.execute(select(User))
            users = result.unique().scalars().all()

            health_repo = SQLAlchemyMemberHealthDataRepository(session)
            details_repo = MemberDetailsRepository(session)
            risk_repo = SQLAlchemyRiskScoreRepository(session)
            scoring_service = HttpEngineScoringAdapter(settings.engine_api_url, client)

            use_case = RecalculateMemberScoresUseCase(
                health_repo, details_repo, risk_repo, scoring_service
            )

            for user in users:
                print(f"Recalculating for user: {user.id}")
                await use_case.execute(user_id=user.id)
                await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
