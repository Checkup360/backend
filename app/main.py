from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.middleware import DBSessionMiddleware
from app.core import settings
from app.routers import auth, organizations, admin

app = FastAPI()

# Registrar DBSessionMiddleware ANTES de otros middlewares
app.add_middleware(DBSessionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(organizations.router)
app.include_router(auth.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"ok": True}

