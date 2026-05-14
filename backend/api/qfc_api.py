from fastapi import APIRouter
from backend.modules.symbolic.symbol_tree_generator import build_qfc_view
from backend.modules.dimensions.containers.container_loader import (
    load_container_by_id,
    load_container_from_file,
)

router = APIRouter()

@router.get("/api/qfc_view/{cid}")
def get_qfc(cid: str):
    if cid.endswith(".json"):
        container = load_container_from_file(cid)
    else:
        container = load_container_by_id(cid)

    return build_qfc_view(container)