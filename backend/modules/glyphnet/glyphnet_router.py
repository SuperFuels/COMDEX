# File: routes/glyphnet_router.py

import logging
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any

from backend.modules.gip.gip_log import gip_log
from backend.modules.glyphnet.glyphnet_packet import push_symbolic_packet, create_gip_packet
from backend.modules.glyphnet.glyphwave_simulator import get_simulation_log  # ✅ NEW import

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/glyphnet", tags=["GlyphNet"])


# ───────────────────────────────────────────────
# 📜 Logs
# ───────────────────────────────────────────────
@router.get("/logs")
def get_glyphnet_logs(limit: Optional[int] = Query(50, ge=1, le=500)):
    """
    Retrieve recent GlyphNet logs.

    Args:
        limit: Maximum number of log entries to return (default: 50, max: 500).
    """
    try:
        logs = gip_log.get_logs(limit=limit)
        return {"status": "ok", "count": len(logs), "logs": logs}
    except Exception as e:
        logger.error(f"[GlyphNetRouter] Failed to fetch logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch GlyphNet logs")


# ───────────────────────────────────────────────
# 🚀 Push
# ───────────────────────────────────────────────
@router.post("/push")
def push_glyphnet_packet(
    payload: Dict[str, Any],
    sender: str = Query(..., description="Identity of the sender"),
    target: Optional[str] = Query(None, description="Optional target identity"),
    packet_type: str = Query("glyph_push", description="Type of symbolic packet"),
):
    """
    Push a symbolic GlyphNet packet into the network.
    """
    try:
        packet = create_gip_packet(
            payload=payload,
            sender=sender,
            target=target,
            packet_type=packet_type,
        )
        success = push_symbolic_packet(packet)

        if not success:
            raise HTTPException(status_code=500, detail="Push rejected by transport layer")

        return {"status": "ok", "packet": packet}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GlyphNetRouter] Failed to push packet: {e}")
        raise HTTPException(status_code=500, detail="Failed to push GlyphNet packet")


# ───────────────────────────────────────────────
# 🎛 Simulation Log
# ───────────────────────────────────────────────
@router.get("/simulations")
def get_glyphnet_simulations(limit: Optional[int] = Query(10, ge=1, le=200)):
    """
    Retrieve recent GlyphWave simulation traces.

    Args:
        limit: Number of recent simulations to return (default: 10, max: 200).
    """
    try:
        logs = get_simulation_log(limit)
        return {"status": "ok", "count": len(logs), "simulations": logs}
    except Exception as e:
        logger.error(f"[GlyphNetRouter] Failed to fetch simulation log: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch GlyphNet simulations")

from backend.modules.glyphnet.agent_identity_registry import validate_agent_token

@router.get("/ws-test")
def glyphnet_ws_test(token: str = Query(..., description="Agent token to validate")):
    """
    Pre-check route for WebSocket clients.
    Lets them verify whether their token will be accepted before attempting the /ws/glyphnet handshake.
    """
    try:
        if validate_agent_token(token):
            return {"status": "ok", "message": "Token valid, WebSocket connection allowed"}
        return {"status": "unauthorized", "message": "Invalid or expired token"}
    except Exception as e:
        logger.error(f"[GlyphNetRouter] Token pre-check failed: {e}")
        raise HTTPException(status_code=500, detail="Token validation error")