# backend/modules/glyphnet/glyphnet_router.py
from __future__ import annotations

import logging
import os
import time
from typing import Optional, Dict, Any

from fastapi import APIRouter, Query, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Optional WS fanout (fallback to no-op if WS layer not present)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from backend.routes.ws.glyphnet_ws import fanout_bus_envelope  # type: ignore
except Exception:
    async def fanout_bus_envelope(*_args, **_kwargs) -> int:  # type: ignore
        return 0

# Existing GlyphNet plumbing
from backend.modules.gip.gip_log import gip_log
from backend.modules.glyphnet.glyphnet_packet import push_symbolic_packet, create_gip_packet
from backend.modules.glyphnet.glyphwave_simulator import get_simulation_log
from backend.modules.photon.validation import validate_photon_capsule
from backend.modules.glyphnet.bus import glyph_bus, topic_for_recipient, envelope_capsule

# Tokens / ACL
from backend.modules.glyphnet.agent_identity_registry import validate_agent_token
try:
    from backend.config_acl import recipient_allowed  # type: ignore
except Exception:
    def recipient_allowed(_: str, __: Any = None) -> bool:  # type: ignore
        return True

# Thread logger (DB-backed preferred)
try:
    from backend.modules.glyphnet.thread_logger import log_thread_event
except Exception:  # type: ignore
    def log_thread_event(*_args, **_kwargs):  # type: ignore
        pass

try:
    # prefer sqlite reader
    from backend.modules.glyphnet.thread_logger import read_thread as _read_thread  # type: ignore
except Exception:
    try:
        # fall back to in-memory helper
        from backend.modules.glyphnet.thread_logger import get_thread_events as _read_thread  # type: ignore
    except Exception:
        def _read_thread(*_args, **_kwargs):  # type: ignore
            return []

# Floor-control manager (broadcasts lock events)
try:
    from backend.modules.glyphnet.lock_manager import LOCKS  # type: ignore
except Exception:
    LOCKS = None  # graceful fallback; we’ll still do a local soft lock below


router = APIRouter(prefix="/api/glyphnet", tags=["GlyphNet"])


# ──────────────────────────────────────────────────────────────────────────────
# Dev token convenience
# ──────────────────────────────────────────────────────────────────────────────
def _extract_token(request: Request, payload: Dict[str, Any]) -> Optional[str]:
    token = payload.get("token")
    if not token:
        token = request.headers.get("x-agent-token") or request.headers.get("X-Agent-Token")
    if not token:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
    return token

def _dev_token_allows(token: Optional[str]) -> bool:
    return os.getenv("GLYPHNET_ALLOW_DEV_TOKEN", "0").lower() in {"1", "true", "yes", "on"} and token in {"dev-token", "local-dev"}

def _agent_id(request: Request) -> str:
    return request.headers.get("X-Agent-Id") or "anonymous"


# ──────────────────────────────────────────────────────────────────────────────
# Simple in-process voice floor (PTT) guard for immediate gating
# (server-wide LOCKS handles broadcast/visibility; this prevents talk-over)
# ──────────────────────────────────────────────────────────────────────────────
_VOICE_LOCKS: Dict[str, Dict[str, Any]] = {}
_LOCK_TTL_SEC = 3.5  # slightly above typical PTT press

def _vkey(channel: str) -> str:
    return f"voice/{channel}"

def _prune(now: float):
    dead = [k for k, v in _VOICE_LOCKS.items() if v.get("until", 0) <= now]
    for k in dead:
        _VOICE_LOCKS.pop(k, None)

def _soft_acquire(channel: str, owner: str) -> Optional[str]:
    """Return None if acquired/extended, or a reason string if busy."""
    now = time.time()
    _prune(now)
    key = _vkey(channel)
    cur = _VOICE_LOCKS.get(key)
    if cur and cur.get("holder") != owner and cur.get("until", 0) > now:
        return f"channel busy (held by {cur.get('holder')})"
    _VOICE_LOCKS[key] = {"holder": owner, "until": now + _LOCK_TTL_SEC}
    return None


# If a central LOCKS manager exists, wire a broadcast callback
if LOCKS:
    def _broadcast_to_topic(topic: str, event: dict):
        try:
            from backend.routes.ws.glyphnet_ws import broadcast_json  # type: ignore
            broadcast_json(topic, event)
        except Exception:
            pass
    LOCKS.set_callback(_broadcast_to_topic)  # type: ignore[attr-defined]


# ──────────────────────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────────────────────
class VoiceFrame(BaseModel):
    channel: str
    seq: int
    ts: int
    mime: str
    data_b64: str


# ──────────────────────────────────────────────────────────────────────────────
# Health & utilities
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/health")
async def glyphnet_health():
    return {"status": "ok", "bus": "inmem"}

@router.get("/logs")
def get_glyphnet_logs(limit: Optional[int] = Query(50, ge=1, le=500)):
    try:
        logs = gip_log.get_logs(limit=limit)
        return {"status": "ok", "count": len(logs), "logs": logs}
    except Exception as e:
        logger.error(f"[GlyphNetRouter] logs failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch GlyphNet logs")

@router.get("/simulations")
def get_glyphnet_simulations(limit: Optional[int] = Query(10, ge=1, le=200)):
    try:
        logs = get_simulation_log(limit)
        return {"status": "ok", "count": len(logs), "simulations": logs}
    except Exception as e:
        logger.error(f"[GlyphNetRouter] simulations failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch GlyphNet simulations")

@router.get("/ws-test")
def glyphnet_ws_test(token: str = Query(...)):
    try:
        if _dev_token_allows(token) or validate_agent_token(token):
            return {"status": "ok", "message": "Token valid, WebSocket allowed"}
        return {"status": "unauthorized", "message": "Invalid or expired token"}
    except Exception as e:
        logger.error(f"[GlyphNetRouter] token pre-check failed: {e}")
        raise HTTPException(status_code=500, detail="Token validation error")


# ──────────────────────────────────────────────────────────────────────────────
# Push symbolic packet (unchanged)
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/push")
def push_glyphnet_packet(
    payload: Dict[str, Any],
    sender: str = Query(..., description="Identity of the sender"),
    target: Optional[str] = Query(None, description="Optional target identity"),
    packet_type: str = Query("glyph_push", description="Type of symbolic packet"),
):
    try:
        packet = create_gip_packet(payload=payload, sender=sender, target=target, packet_type=packet_type)
        success = push_symbolic_packet(packet)
        if not success:
            raise HTTPException(status_code=500, detail="Push rejected by transport layer")
        return {"status": "ok", "packet": packet}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GlyphNetRouter] push failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to push GlyphNet packet")


# ──────────────────────────────────────────────────────────────────────────────
# 📦 TX endpoint: entanglement_lock | voice_frame | glyphs/glyph_stream
# Path is /api/glyphnet/tx (thanks to router prefix)
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/tx")
async def glyphnet_tx(payload: Dict[str, Any], request: Request):
    # --- Auth gate (dev-token allowed if env toggled) ---
    token = _extract_token(request, payload)
    if not (_dev_token_allows(token) or (token and validate_agent_token(token))):
        raise HTTPException(status_code=401, detail="Unauthorized (invalid or missing token)")

    recipient = payload.get("recipient") or payload.get("topic")
    capsule   = payload.get("capsule") or {}
    meta: Dict[str, Any] = payload.get("meta") or {}

    if not isinstance(recipient, str) or not recipient:
        raise HTTPException(status_code=400, detail="recipient must be a non-empty string")

    # --- ACL ---
    try:
        allowed = recipient_allowed(recipient, request.headers)  # type: ignore[arg-type]
    except TypeError:
        allowed = recipient_allowed(recipient)                   # type: ignore[call-arg]
    if not allowed:
        raise HTTPException(status_code=403, detail=f"Recipient not allowed: {recipient}")

    topic    = topic_for_recipient(recipient)
    agent_id = _agent_id(request)
    graph    = (meta.get("graph") or "personal").lower()

    # ========== 1) entanglement_lock (PTT floor control) ==========
    lock = (capsule or {}).get("entanglement_lock")
    if lock is not None:
        op       = (lock.get("op") or "acquire").lower()
        # IMPORTANT: default to ucs:// recipient (not gnet: topic)
        resource = lock.get("resource") or f"voice:{recipient}"
        owner    = (lock.get("owner") or agent_id)
        ttl_ms   = int(lock.get("ttl_ms") or 3500)

        # If LOCKS isn’t available, return a safe dev-stub so the UI proceeds.
        if not LOCKS or not hasattr(LOCKS, "apply"):
            state   = "free" if op == "release" else "held"
            granted = (op == "acquire" and state == "held")
            lock_event = {
                "type": "entanglement_lock",
                "resource": resource,
                "owner": owner,
                "state": state,
                "granted": granted,
                "until": None,
            }
            # Best-effort broadcast even in dev-stub
            try:
                from backend.routes.ws.glyphnet_ws import broadcast_event_throttled as broadcast_json  # type: ignore
                broadcast_json({**lock_event, "topic": topic})
            except Exception:
                pass
            return {"status": "ok", "lock": lock_event}

        # Real lock manager
        try:
            ev = LOCKS.apply(topic=topic, op=op, resource=resource, owner=owner, ttl_ms=ttl_ms)  # type: ignore[attr-defined]
        except Exception as e:
            # Surface deny as OK so the UI can react (avoid CORS/red-herring errors)
            lock_event = {
                "type": "entanglement_lock",
                "resource": resource,
                "owner": owner,
                "state": "free",
                "granted": False,
                "error": f"{e}",
            }
            try:
                from backend.routes.ws.glyphnet_ws import broadcast_event_throttled as broadcast_json  # type: ignore
                broadcast_json({**lock_event, "topic": topic})
            except Exception:
                pass
            return {"status": "ok", "lock": lock_event}

        # Normalize + ensure explicit grant/deny
        state   = ev.get("state") or ("held" if ev.get("until") else "free")
        granted = ev.get("granted")
        if granted is None and op == "acquire":
            granted = (state == "held" and (ev.get("owner") == owner))

        lock_event = {
            "type": "entanglement_lock",
            "resource": resource,
            "owner": ev.get("owner") or owner,
            "state": state,
            "until": ev.get("until"),
            "granted": bool(granted),
        }

        # Broadcast BEFORE returning so other tabs sync immediately
        try:
            from backend.routes.ws.glyphnet_ws import broadcast_event_throttled as broadcast_json  # type: ignore
            broadcast_json({**lock_event, "topic": topic})
        except Exception:
            pass

        # Optional: append to thread log (never break response)
        try:
            log_thread_event(topic, {
                "type": "lock",
                "graph": graph,
                "ts": time.time(),
                "from": owner,
                "to": recipient,
                "payload": lock_event,
            }, direction="out", user_id=owner)
        except Exception:
            pass

        return {"status": "ok", "lock": lock_event}

    # ========== 2) voice_frame ==========
    if "voice_frame" in capsule:
        try:
            vf = VoiceFrame(**capsule["voice_frame"])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"invalid voice_frame: {e}")

        # Local soft gate to avoid talk-over
        busy_reason = _soft_acquire(vf.channel, agent_id)
        if busy_reason:
            return {"status": "busy", "reason": busy_reason, "channel": vf.channel, "seq": vf.seq}

        env = {
            "id": f"vf-{int(time.time()*1000)}-{vf.seq}",
            "type": "glyphnet_voice_frame",
            "recipient": recipient,
            "capsule": {"voice_frame": vf.dict()},
            "meta": meta,
            "sender": agent_id,
            "ts": int(time.time() * 1000),
        }

        try:
            delivered = await glyph_bus.publish(topic, env)
        except Exception as e:
            logger.error(f"[GlyphNetTX] bus.publish (voice) error: {e}")
            delivered = 0

        if not delivered:
            try:
                delivered = await fanout_bus_envelope(topic, env)
            except Exception as e:
                logger.warning(f"[GlyphNetTX] WS fallback (voice) failed: {e}")

        try:
            log_thread_event(topic, {
                "graph": graph,
                "type": "voice",
                "ts": time.time(),
                "from": agent_id,
                "to": recipient,
                "payload": {
                    "mime": vf.mime,
                    "seq": vf.seq,
                    "channel": vf.channel,
                    "bytes_b64": vf.data_b64,
                },
            }, direction="out", user_id=agent_id)
        except Exception:
            pass

        until = _VOICE_LOCKS.get(_vkey(vf.channel), {}).get("until")
        return {
            "status": "ok",
            "kind": "voice_frame",
            "delivered": int(delivered or 0),
            "channel": vf.channel,
            "seq": vf.seq,
            "lock_until": until,
            "topic": topic,
            "msg_id": env.get("id"),
        }

    # ========== 3) text capsules ==========
    if not (capsule.get("glyphs") or capsule.get("glyph_stream")):
        raise HTTPException(status_code=400, detail="capsule must contain glyphs/glyph_stream or voice_frame")

    try:
        validate_photon_capsule(capsule)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid photon capsule: {e}")

    env = envelope_capsule(recipient, capsule, meta)

    try:
        delivered = await glyph_bus.publish(topic, env)
    except Exception as e:
        logger.error(f"[GlyphNetTX] bus.publish (text) error: {e}")
        delivered = 0

    if not delivered:
        try:
            delivered = await fanout_bus_envelope(topic, env)
        except Exception as e:
            logger.warning(f"[GlyphNetTX] WS fallback (text) failed: {e}")

    try:
        glyphs = capsule.get("glyphs") or []
        stream = capsule.get("glyph_stream") or []
        text_val = glyphs[0] if (isinstance(glyphs, list) and glyphs) else (stream[0] if (isinstance(stream, list) and stream) else None)
        log_thread_event(topic, {
            "graph": graph,
            "type": "text",
            "ts": time.time(),
            "from": agent_id,
            "to": recipient,
            "payload": {"text": text_val},
        }, direction="out", user_id=agent_id)
    except Exception:
        pass

    return {"status": "ok", "kind": "capsule", "delivered": int(delivered or 0), "topic": topic, "msg_id": env.get("id")}
    
# ──────────────────────────────────────────────────────────────────────────────
# Thread fetch (KG-backed)
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/thread")
def get_thread(topic: str, kg: str = "personal", limit: int = 100):
    try:
        events = _read_thread(topic, kg, limit)
        return {"status": "ok", "topic": topic, "graph": kg, "count": len(events or []), "events": events or []}
    except Exception as e:
        logger.error(f"[GlyphNetRouter] get_thread failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to read thread")