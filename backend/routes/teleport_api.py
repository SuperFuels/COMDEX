# File: backend/routes/api/teleport_api.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend.modules.dna_chain.teleport import teleport
from backend.modules.dna_chain.dc_handler import handle_object_interaction
from backend.modules.runtime.container_runtime import teleport_to_linked_container  # ✅ Add this import

router = APIRouter()

class TeleportRequest(BaseModel):
    source: str
    destination: str = None
    object_id: str = None
    reason: str = "api_manual"

@router.post("/api/aion/teleport")
def trigger_teleport(request: TeleportRequest):
    if request.object_id:
        success = handle_object_interaction(request.source, request.object_id)
        if not success:
            raise HTTPException(status_code=404, detail="Teleporter object not found or no teleport target.")
        return {"status": "teleport_triggered", "via": "object", "object_id": request.object_id}

    if request.destination:
        teleport(request.source, request.destination, reason=request.reason)
        return {"status": "teleport_triggered", "via": "manual", "destination": request.destination}

    raise HTTPException(status_code=400, detail="Either object_id or destination must be provided.")


# ✅ NEW GET endpoint for GHX/Atom UI
@router.get("/api/teleport/{container_id}")
def teleport_to_container(container_id: str):
    """
    Used by the GHX/Atom Electron UI to teleport to a linked container.
    """
    try:
        result = teleport_to_linked_container(container_id)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Teleport failed: {str(e)}")