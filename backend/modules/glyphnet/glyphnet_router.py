# File: backend/modules/glyphnet/glyphnet_router.py
from __future__ import annotations

import logging
import os
from typing import Optional, Dict, Any

from fastapi import APIRouter, Query, HTTPException, Request

# Existing GlyphNet WS fanout helper
from backend.routes.ws.glyphnet_ws import fanout_bus_envelope

# Existing GlyphNet/GIP plumbing
from backend.modules.gip.gip_log import gip_log
from backend.modules.glyphnet.glyphnet_packet import (
    push_symbolic_packet,
    create_gip_packet,
)
from backend.modules.glyphnet.glyphwave_simulator import get_simulation_log

# Capsule TX path and validation
from backend.modules.photon.validation import validate_photon_capsule
from backend.modules.glyphnet.bus import (
    glyph_bus,
    topic_for_recipient,
    envelope_capsule,
)

# Token pre-check
from backend.modules.glyphnet.agent_identity_registry import validate_agent_token

# Optional recipient ACL (safe to miss)
try:
    from backend.config_acl import recipient_allowed  # type: ignore
except Exception:
    def recipient_allowed(_: str) -> bool:
        return True

logger = logging.getLogger(__name__)

# Unified prefix for all GlyphNet HTTP routes
router = APIRouter(prefix="/api/glyphnet", tags=["GlyphNet"])


# ───────────────────────────────────────────────
# 🩺 Health
# ───────────────────────────────────────────────
@router.get("/health")
async def glyphnet_health():
    """Simple health probe for the in-memory GlyphNet bus."""
    return {"status": "ok", "bus": "inmem"}


# ───────────────────────────────────────────────
# 📜 Logs
# ───────────────────────────────────────────────
@router.get("/logs")
def get_glyphnet_logs(limit: Optional[int] = Query(50, ge=1, le=500)):
    """Retrieve recent GlyphNet logs."""
    try:
        logs = gip_log.get_logs(limit=limit)
        return {"status": "ok", "count": len(logs), "logs": logs}
    except Exception as e:
        logger.error(f"[GlyphNetRouter] Failed to fetch logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch GlyphNet logs")


# ───────────────────────────────────────────────
# 🚀 Push (symbolic GIP packet)
# ───────────────────────────────────────────────
@router.post("/push")
def push_glyphnet_packet(
    payload: Dict[str, Any],
    sender: str = Query(..., description="Identity of the sender"),
    target: Optional[str] = Query(None, description="Optional target identity"),
    packet_type: str = Query("glyph_push", description="Type of symbolic packet"),
):
    """Push a symbolic GlyphNet packet into the network via the GIP layer."""
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
    """Retrieve recent GlyphWave simulation traces."""
    try:
        logs = get_simulation_log(limit)
        return {"status": "ok", "count": len(logs), "simulations": logs}
    except Exception as e:
        logger.error(f"[GlyphNetRouter] Failed to fetch simulation log: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch GlyphNet simulations")


# ───────────────────────────────────────────────
# 🔐 Token pre-check for WS clients
# ───────────────────────────────────────────────
@router.get("/ws-test")
def glyphnet_ws_test(token: str = Query(..., description="Agent token to validate")):
    """
    Pre-check route for WebSocket clients to verify token before /ws/glyphnet handshake.
    """
    try:
        if validate_agent_token(token):
            return {"status": "ok", "message": "Token valid, WebSocket connection allowed"}
        return {"status": "unauthorized", "message": "Invalid or expired token"}
    except Exception as e:
        logger.error(f"[GlyphNetRouter] Token pre-check failed: {e}")
        raise HTTPException(status_code=500, detail="Token validation error")


# ───────────────────────────────────────────────
# 📦 Capsule TX (publish to recipient topic)
# ───────────────────────────────────────────────
def _extract_token(request: Request, payload: Dict[str, Any]) -> Optional[str]:
    """Prefer body.token, then X-Agent-Token, then Authorization: Bearer."""
    token = payload.get("token")
    if not token:
        token = request.headers.get("x-agent-token")
    if not token:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
    return token

def _dev_token_allows(token: Optional[str]) -> bool:
    """Allow only the literal dev-token when GLYPHNET_ALLOW_DEV_TOKEN=1."""
    return os.getenv("GLYPHNET_ALLOW_DEV_TOKEN", "0") == "1" and token == "dev-token"

@router.post("/tx")
async def glyphnet_tx(payload: Dict[str, Any], request: Request):
    """
    Transmit a Photon capsule to a recipient over the in-memory GlyphNet bus.

    Body:
    {
      "recipient": "ucs://local/ucs_hub" | "gnet:ucs://local/ucs_hub",
      "capsule": { ...validated photon capsule... },
      "meta": { ...optional... },
      "token": "optional-dev-token"   # alternative to headers
    }

    Headers (either works):
      X-Agent-Token: <token>
      Authorization: Bearer <token>
    """
    # ---- Token gate (dev-token allowed if flagged) ----
    token = _extract_token(request, payload)
    if not _dev_token_allows(token):
        if not token or not validate_agent_token(token):
            raise HTTPException(status_code=401, detail="Unauthorized (invalid or missing token)")

    # ---- Body validation ----
    recipient = payload.get("recipient")
    capsule = payload.get("capsule")
    meta: Optional[Dict[str, Any]] = payload.get("meta") or {}

    if not isinstance(recipient, str) or not recipient:
        raise HTTPException(400, "recipient must be a non-empty string")

    if not recipient_allowed(recipient):
        raise HTTPException(status_code=403, detail=f"Recipient not allowed: {recipient}")

    if not isinstance(capsule, dict):
        raise HTTPException(400, "capsule must be an object")

    # Validate photon capsule (supports glyph_stream/glyphs)
    try:
        validate_photon_capsule(capsule)
    except Exception as e:
        raise HTTPException(400, f"Invalid photon capsule: {e}")

    # ucs://… → gnet:ucs://…  (gnet: literal is also accepted)
    topic = topic_for_recipient(recipient)

    # Normalize into standard envelope (id/ts/op/recipient/capsule/meta)
    env = envelope_capsule(recipient, capsule, meta)

    # Publish to in-mem bus
    try:
        delivered = await glyph_bus.publish(topic, env)
    except Exception as e:
        logger.error(f"[GlyphNetTX] bus.publish error: {e}")
        delivered = 0

    # Dev fallback: mirror to WS clients on this topic when no subs were present
    if not delivered:
        try:
            delivered = await fanout_bus_envelope(topic, env)
        except Exception as e:
            logger.warning(f"[GlyphNetTX] WS fallback failed: {e}")

    return {
        "status": "ok",
        "delivered": int(delivered or 0),
        "topic": topic,
        "msg_id": env.get("id"),
    }