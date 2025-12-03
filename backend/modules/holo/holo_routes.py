# backend/modules/holo/holo_routes.py
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from backend.modules.holo.holo_service import export_holo_from_container
from backend.modules.runtime.container_runtime import get_container_runtime

router = APIRouter(
    prefix="/holo",
    tags=["holo"],
)

@router.post("/export/{container_id}")
def export_holo(
    container_id: str,
    view_ctx: Dict[str, Any] = Body(default={}),
    revision: int = 1,
):
    """
    POST /api/holo/export/{container_id}?revision=1
    body = view_ctx:
      {
        "tick": 123,
        "reason": "devtools_manual_export",
        "source_view": "qfc",
        "frame": "original",
        ...
      }
    """
    try:
        cr = get_container_runtime()

        # either this:
        if hasattr(cr, "load_and_activate_container"):
            container = cr.load_and_activate_container(container_id)
        else:
            # fallback to whatever you have in your runtime
            cr.set_active_container(container_id)
            container = cr.get_decrypted_current_container()

        holo = export_holo_from_container(container, view_ctx, revision=revision)
        return getattr(holo, "__dict__", holo)

    except Exception as e:
        # print full traceback to the backend logs
        import traceback
        traceback.print_exc()
        # return a readable error to curl
        raise HTTPException(
            status_code=500,
            detail=f"holo_export_failed: {type(e).__name__}: {e}",
        )