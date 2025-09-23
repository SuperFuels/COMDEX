# File: backend/routes/api/teleport_api.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.modules.dna_chain.teleport import teleport
from backend.modules.dna_chain.dc_handler import handle_object_interaction
from backend.modules.runtime.container_runtime import teleport_to_linked_container

router = APIRouter(prefix="/api", tags=["Teleport"])


# -----------------------
# Models
# -----------------------
class TeleportRequest(BaseModel):
    source: str
    destination: str | None = None
    object_id: str | None = None
    reason: str = "api_manual"


# -----------------------
# Routes
# -----------------------
@router.post("/aion/teleport")
def trigger_teleport(request: TeleportRequest):
    """
    Trigger teleportation either by:
    - object_id (via object interaction)
    - destination (manual request)
    """
    if request.object_id:
        success = handle_object_interaction(request.source, request.object_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Teleporter object not found or no teleport target.",
            )
        return {
            "status": "teleport_triggered",
            "via": "object",
            "object_id": request.object_id,
        }

    if request.destination:
        teleport(request.source, request.destination, reason=request.reason)
        return {
            "status": "teleport_triggered",
            "via": "manual",
            "destination": request.destination,
        }

    raise HTTPException(
        status_code=400,
        detail="Either object_id or destination must be provided.",
    )


@router.get("/teleport/{container_id}")
def teleport_to_container(container_id: str):
    """
    Used by the GHX/Atom UI to teleport to a linked container.
    """
    try:
        result = teleport_to_linked_container(container_id)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Teleport failed: {e}",
        )