from fastapi import APIRouter

router = APIRouter(prefix="/organizations", tags=["orgs"])


@router.get("/")
def list_orgs():
    return {"orgs": "no orgs"}
