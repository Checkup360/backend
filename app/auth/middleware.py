from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import async_session_maker


class DBSessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware que inyecta una DB session en request.state.db
    para que UserManager pueda acceder a la BD desde los callbacks de OAuth.
    """

    async def dispatch(self, request: Request, call_next):
        async with async_session_maker() as session:
            request.state.db = session
            response = await call_next(request)
        return response
