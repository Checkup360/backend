from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.middleware import DBSessionMiddleware
from app.auth.pending_invite_middleware import PendingInviteCookieMiddleware
from app.core import settings
from app.routers import admin, auth, invites, organizations

app = FastAPI()

# Primero el que limpia cookie de invite al final de la respuesta (corre último al salir).
app.add_middleware(PendingInviteCookieMiddleware)
app.add_middleware(DBSessionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Location"],
)

app.include_router(organizations.router)
app.include_router(auth.router)
app.include_router(invites.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"ok": True}

