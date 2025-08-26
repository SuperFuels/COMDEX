from fastapi import APIRouter
from backend.modules.symbolic.symbol_tree_generator import build_qfc_view
from backend.modules.runtime.container_runtime import load_container

router = APIRouter()

@router.get("/api/qfc_view/{cid}")
def get_qfc(cid: str):
    container = load_container(cid)
    return build_qfc_view(container)