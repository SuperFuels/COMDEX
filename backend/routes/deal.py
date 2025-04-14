from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def list_deals():
    return {"msg": "Deal route placeholder"}

