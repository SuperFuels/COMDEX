# backend/routes/glyphnet_transport_api.py

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from backend.modules.glyphnet.glyphnet_packet import create_glyph_packet
from backend.modules.glyphnet.glyph_transport_switch import route_gip_packet
from backend.modules.glyphnet.glyphnet_trace import (
    get_recent_traces,
    GLYPHNET_TRACE_BUFFER,
)

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


# ✅ NEW: GlyphNet Trace Retrieval Endpoint
@router.get("/trace")
async def get_trace(
    snapshot_id: Optional[str] = Query(None, description="Filter traces by snapshot ID"),
    glyph_id: Optional[str] = Query(None, description="Filter by specific glyph ID"),
    limit: int = Query(100, ge=1, le=500, description="Max number of traces to return"),
):
    """
    Retrieve GlyphNet execution traces, filtered by snapshot or glyph ID.
    """
    try:
        traces = get_recent_traces(limit=limit)

        # Filter by snapshot_id or glyph_id if provided
        if snapshot_id:
            traces = [t for t in traces if t["data"].get("snapshot_id") == snapshot_id]
        if glyph_id:
            traces = [t for t in traces if t["data"].get("glyph_id") == glyph_id]

        return {"count": len(traces), "traces": traces}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve traces: {str(e)}")