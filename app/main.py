from fastapi import FastAPI

from app.routers import auth, organizations

app = FastAPI()
app.include_router(organizations.router)
app.include_router(auth.router)

@app.get("/")
def root():
    return {"ok": True}

