from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional

from backend.modules.photon.photon_binary_bridge import PhotonBinaryBridge

router = APIRouter(prefix="/api/photon", tags=["photon"])

class GwipToCapsuleReq(BaseModel):
    gwip_packet: Dict[str, Any]
    sender_id: str = "frontend"
    receiver_id: str = "photon_core"
    include_qkd: bool = True
    mode: str = "auto"          # "auto" | "photon" | "binary"

@router.post("/gwip-to-capsule")
async def gwip_to_capsule(req: GwipToCapsuleReq):
    bridge = PhotonBinaryBridge(mode=req.mode)
    # wave is "Any" in your module; for now pass a stub unless you have a real wave object
    wave_stub: Any = {"phase": req.gwip_packet.get("envelope", {}).get("phase", 0.0)}
    capsule = await bridge.gwip_to_photon_capsule(
        gwip_packet=req.gwip_packet,
        sender_id=req.sender_id,
        receiver_id=req.receiver_id,
        wave=wave_stub,
        include_qkd=req.include_qkd,
    )
    return capsule