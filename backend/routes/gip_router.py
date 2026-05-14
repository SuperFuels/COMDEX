from fastapi import APIRouter, Request
from backend.modules.gip.gip_executor import execute_gip_packet
from pydantic import BaseModel
from typing import Any

router = APIRouter()

class GIPInput(BaseModel):
    packet: dict[str, Any]

@router.post("/gip/receive")
async def receive_gip_packet(payload: GIPInput):
    try:
        result = execute_gip_packet(payload.packet)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
