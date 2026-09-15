from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.infrastructure.authentication.middleware.db_session import DBSessionMiddleware
from app.infrastructure.authentication.middleware.pending_invite import (
    PendingInviteCookieMiddleware,
)
from app.infrastructure.config import settings
from app.infrastructure.persistence.database import get_db
from app.presentation.api.routers import (
    admin,
    auth,
    invites,
    members,
    organizations,
    assessments,
)

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

uploads_path = Path(settings.upload_dir)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(uploads_path)), name="media")

app.add_middleware(PendingInviteCookieMiddleware)
app.add_middleware(DBSessionMiddleware)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Location", "X-Total-Count", "X-Page", "X-Page-Size"],
)

app.include_router(organizations.router)
app.include_router(auth.router)
app.include_router(invites.router)
app.include_router(members.router)
app.include_router(assessments.router)
app.include_router(assessments.submissions_router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"ok": True}


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "unreachable"},
        )
