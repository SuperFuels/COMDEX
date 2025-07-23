# backend/routes/glyphnet_transport_api.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from backend.modules.glyphnet.glyphnet_packet import create_glyph_packet
from backend.modules.glyphnet.glyph_transport_switch import route_gip_packet

router = APIRouter(prefix="/glyphnet/transport", tags=["GlyphNet Transport"])


class TransportRequest(BaseModel):
    payload: Dict[str, Any]
    transport: str
    options: Optional[Dict[str, Any]] = None


@router.post("/send")
async def send_packet(req: TransportRequest):
    try:
        packet = create_glyph_packet(req.payload)
        success = route_gip_packet(packet, req.transport, req.options)
        if not success:
            raise HTTPException(status_code=400, detail="Transport failed")
        return {"status": "ok", "transport": req.transport}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))