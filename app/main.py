from fastapi import FastAPI
from app.routers import organizations

app = FastAPI()
app.include_router(organizations.router)

@app.get("/")
def root():
    return {"ok": True}
