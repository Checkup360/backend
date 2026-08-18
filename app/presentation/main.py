from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.infrastructure.authentication.middleware.db_session import DBSessionMiddleware
from app.infrastructure.authentication.middleware.pending_invite import (
    PendingInviteCookieMiddleware,
)
from app.infrastructure.config import settings
from app.presentation.api.routers import (
    admin,
    auth,
    invites,
    members,
    organizations,
)

app = FastAPI()

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
app.include_router(admin.router)


@app.get("/")
def root():
    return {"ok": True}
