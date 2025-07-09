# File: backend/routes/teleport_api.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.modules.dna_chain.teleport import teleport
from backend.modules.dna_chain.dc_handler import handle_object_interaction

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
