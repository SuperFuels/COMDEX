# backend/api/teleport_handler.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.modules.runtime.container_runtime import ContainerRuntime

router = APIRouter()

class TeleportRequest(BaseModel):
    container_id: str

@router.post("/api/teleport")
def teleport_to_container(payload: TeleportRequest):
    container_id = payload.container_id
    try:
        runtime = ContainerRuntime()
        result = runtime.load_and_activate_container(container_id)
        return {"success": True, "container": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Teleport failed: {str(e)}")