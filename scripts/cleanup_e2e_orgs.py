import asyncio
import re
from sqlalchemy import text
from app.infrastructure.persistence.database import async_session_maker


async def cleanup():
    async with async_session_maker() as session:
        result = await session.execute(text("SELECT id, name FROM organizations"))
        orgs = result.fetchall()
        pattern = re.compile(r"\d{13}-[a-z0-9]+$", re.IGNORECASE)
        to_delete = [org.id for org in orgs if pattern.search(org.name)]

        if not to_delete:
            print("No E2E orgs found.")
            return

        print(f"Deleting {len(to_delete)} E2E orgs...")
        for org_id in to_delete:
            await session.execute(
                text("DELETE FROM organizations WHERE id = :id"), {"id": org_id}
            )

        await session.commit()
        print("Deleted.")


if __name__ == "__main__":
    asyncio.run(cleanup())
