# backend/modules/glyphnet/glyphnet_router.py
from __future__ import annotations

import logging
import os
import time
from typing import Optional, Dict, Any

from fastapi import APIRouter, Query, HTTPException, Request
from pydantic import BaseModel

# --- Optional WS fanout (dev fallback) ---
try:
    from backend.routes.ws.glyphnet_ws import fanout_bus_envelope  # type: ignore
except Exception:
    async def fanout_bus_envelope(*_args, **_kwargs) -> int:
        # no-op fallback when WS helper isn't available
        return 0

# Existing GlyphNet/GIP plumbing
from backend.modules.gip.gip_log import gip_log
from backend.modules.glyphnet.glyphnet_packet import push_symbolic_packet, create_gip_packet
from backend.modules.glyphnet.glyphwave_simulator import get_simulation_log

# Capsule TX path and validation
from backend.modules.photon.validation import validate_photon_capsule
from backend.modules.glyphnet.bus import glyph_bus, topic_for_recipient, envelope_capsule

# Token pre-check
from backend.modules.glyphnet.agent_identity_registry import validate_agent_token

# Optional recipient ACL (may accept headers or not depending on your impl)
try:
    from backend.config_acl import recipient_allowed  # type: ignore
except Exception:
    def recipient_allowed(_: str, __: Any = None) -> bool:
        return True

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/glyphnet", tags=["GlyphNet"])

# ───────────────────────────────────────────────
# 🔒 Simple floor-control lock for PTT (in-memory)
#   key: "voice/<channel>" -> { holder:str, until:float }
# ───────────────────────────────────────────────
_VOICE_LOCKS: Dict[str, Dict[str, Any]] = {}
_LOCK_TTL_SEC = 3.0  # basic PTT hold window

def _lock_key(channel: str) -> str:
    return f"voice/{channel}"

def _prune_locks(now: float):
    # remove expired locks
    dead = [k for k, v in _VOICE_LOCKS.items() if v.get("until", 0) <= now]
    for k in dead:
        _VOICE_LOCKS.pop(k, None)

def _acquire_or_check_lock(channel: str, sender: str) -> Optional[str]:
    """
    Returns None if allowed.
    Returns a string reason if blocked.
    """
    now = time.time()
    _prune_locks(now)
    key = _lock_key(channel)
    lock = _VOICE_LOCKS.get(key)
    if lock:
        holder = lock.get("holder")
        if holder != sender and lock.get("until", 0) > now:
            return f"channel busy (held by {holder})"
    # (soft) acquire/extend lock for sender
    _VOICE_LOCKS[key] = {"holder": sender, "until": now + _LOCK_TTL_SEC}
    return None



# ───────────────────────────────────────────────
# 🧾 Models for voice_frame TX
# ───────────────────────────────────────────────
class VoiceFrame(BaseModel):
    channel: str
    seq: int
    ts: int
    mime: str
    data_b64: str


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
# 🪪 Token helpers
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
    return os.getenv("GLYPHNET_ALLOW_DEV_TOKEN", "0") in {"1", "true", "yes", "on"} and token in {"dev-token", "local-dev"}


# ───────────────────────────────────────────────
# 📦 Capsule TX (glyphs/glyph_stream) + 🎙 voice_frame
# ───────────────────────────────────────────────
@router.post("/tx")
async def glyphnet_tx(payload: Dict[str, Any], request: Request):
    """
    Transmit to a recipient over the in-memory GlyphNet bus.

    Body:
    {
      "recipient": "ucs://local/ucs_hub" | "gnet:ucs://local/ucs_hub",
      "capsule": {
        # EITHER normal photon capsule:
        "glyphs": [...], "glyph_stream": [...]
        # OR voice:
        "voice_frame": { "channel","seq","ts","mime","data_b64" }
      },
      "meta": { ...optional... },
      "token": "optional-dev-token"
    }

    Headers (either works):
      X-Agent-Token: <token>
      Authorization: Bearer <token>
      X-Agent-Id: <sender-id>   # optional, for voice locks/telemetry
    """
    # ---- Token gate (dev-token allowed if flagged) ----
    token = _extract_token(request, payload)
    if not _dev_token_allows(token):
        if not token or not validate_agent_token(token):
            raise HTTPException(status_code=401, detail="Unauthorized (invalid or missing token)")

    # ---- Body extraction ----
    recipient = payload.get("recipient")
    capsule = payload.get("capsule")
    meta: Optional[Dict[str, Any]] = payload.get("meta") or {}

    if not isinstance(recipient, str) or not recipient:
        raise HTTPException(status_code=400, detail="recipient must be a non-empty string")

    # Enforce ACL (support both signatures: with or without headers)
    try:
        allowed = recipient_allowed(recipient, request.headers)  # type: ignore[arg-type]
    except TypeError:
        allowed = recipient_allowed(recipient)  # type: ignore[call-arg]
    if not allowed:
        raise HTTPException(status_code=403, detail=f"Recipient not allowed: {recipient}")

    if not isinstance(capsule, dict):
        raise HTTPException(status_code=400, detail="capsule must be an object")

    # Normalize topic (ucs://... → gnet:ucs://...)
    topic = topic_for_recipient(recipient)

    # ── Path A: voice_frame (skip photon validation) ─────────────────────────
    vf_raw = capsule.get("voice_frame")
    if vf_raw is not None:
        try:
            vf = VoiceFrame(**vf_raw)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"invalid voice_frame: {e}")

        sender = request.headers.get("X-Agent-Id", "anonymous")
        reason = _acquire_or_check_lock(vf.channel, sender)
        if reason:
            # Busy receipt; clients use this for UI indicators / retry backoff
            return {
                "status": "busy",
                "reason": reason,
                "channel": vf.channel,
                "seq": vf.seq,
            }

        env = {
            "id": f"vf-{int(time.time()*1000)}-{vf.seq}",
            "type": "glyphnet_voice_frame",
            "recipient": recipient,
            "capsule": {"voice_frame": vf.dict()},
            "meta": meta or {},
            "sender": sender,
            "ts": int(time.time() * 1000),
        }

        try:
            delivered = await glyph_bus.publish(topic, env)
        except Exception as e:
            logger.error(f"[GlyphNetTX] voice publish error: {e}")
            delivered = 0

        if not delivered:
            try:
                delivered = await fanout_bus_envelope(topic, env)
            except Exception as e:
                logger.warning(f"[GlyphNetTX] WS fallback (voice) failed: {e}")

        return {
            "status": "ok",
            "kind": "voice_frame",
            "delivered": int(delivered or 0),
            "channel": vf.channel,
            "seq": vf.seq,
            "lock_until": _VOICE_LOCKS[_lock_key(vf.channel)]["until"],
            "topic": topic,
            "msg_id": env.get("id"),
        }

    # ── Path B: normal photon capsule (glyphs / glyph_stream) ───────────────
    try:
        # Only validate for photon capsules
        if capsule.get("glyphs") or capsule.get("glyph_stream"):
            validate_photon_capsule(capsule)
        else:
            raise HTTPException(status_code=400, detail="capsule must contain glyphs/glyph_stream or voice_frame")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid photon capsule: {e}")

    env = envelope_capsule(recipient, capsule, meta)

    try:
        delivered = await glyph_bus.publish(topic, env)
    except Exception as e:
        logger.error(f"[GlyphNetTX] bus.publish error: {e}")
        delivered = 0

    if not delivered:
        try:
            delivered = await fanout_bus_envelope(topic, env)
        except Exception as e:
            logger.warning(f"[GlyphNetTX] WS fallback failed: {e}")

    return {
        "status": "ok",
        "kind": "capsule",
        "delivered": int(delivered or 0),
        "topic": topic,
        "msg_id": env.get("id"),
    }
