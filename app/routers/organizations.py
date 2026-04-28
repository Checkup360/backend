from fastapi import APIRouter, Depends

router = APIRouter(prefix="/organizations", tags=["orgs"])

@router.get("/")
def list_orgs():
    return {"orgs":"no orgs"}
