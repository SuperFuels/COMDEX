# File: backend/modules/gip/gip_adapter_http.py

import requests
from typing import Dict, Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from .gip_packet import create_gip_packet

# -------------------------------------------------------------------
# Low-level helper (kept as-is)
# -------------------------------------------------------------------
def send_gip_packet_http(destination_url: str, packet_type: str, channel: str, payload: dict) -> dict:
    """
    Send a GIP packet over HTTP POST.
    """
    packet = create_gip_packet(packet_type, channel, payload)
    try:
        response = requests.post(destination_url, json=packet, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "packet": packet}

# Example:
# send_gip_packet_http("https://glyphnet-node.io/gip", "teleport", "luxnet", {"coords": [0,1,2]})

# -------------------------------------------------------------------
# FastAPI router (new)
# -------------------------------------------------------------------
router = APIRouter()

@router.get("/gip/health")
async def gip_health():
    return {"ok": True, "service": "gip_adapter_http"}

class SendPacketBody(BaseModel):
    destination_url: str
    packet_type: str
    channel: str
    payload: Dict[str, Any]

@router.post("/gip/send")
async def gip_send(body: SendPacketBody):
    """
    Build a GIP packet and POST it to destination_url.
    """
    result = send_gip_packet_http(
        destination_url=body.destination_url,
        packet_type=body.packet_type,
        channel=body.channel,
        payload=body.payload,
    )
    return {"status": "ok" if "error" not in result else "error", "result": result}

class BuildPacketBody(BaseModel):
    packet_type: str
    channel: str
    payload: Dict[str, Any]
    include_meta: Optional[bool] = True

@router.post("/gip/packet")
async def gip_build_packet(body: BuildPacketBody):
    """
    Just build and return the GIP packet (no network call).
    """
    packet = create_gip_packet(body.packet_type, body.channel, body.payload)
    return {"packet": packet}

# Compatibility export so older code can do `from ... import routes`
routes = router
__all__ = ["router", "routes", "send_gip_packet_http"]