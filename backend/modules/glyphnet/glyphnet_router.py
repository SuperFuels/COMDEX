# backend/modules/glyphnet/glyphnet_router.py
from __future__ import annotations

import logging
import os
import time
from typing import Optional, Dict, Any

from fastapi import APIRouter, Query, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
MAX_GLYPHS   = int(os.getenv("MAX_GLYPHS", "65536"))
MAX_TEXT_LEN = int(os.getenv("MAX_TEXT_LEN", "200000"))

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

# ── add with the other imports
import json, hashlib, threading

# ──────────────────────────────────────────────────────────────
# Canonical id + lightweight de-dup cache (TTL)
# ──────────────────────────────────────────────────────────────
_SEEN_IDS: Dict[str, float] = {}
_SEEN_LOCK = threading.Lock()
_SEEN_TTL_SEC = 60.0  # keep last minute of ids

def _seen_prune(now: float | None = None) -> None:
    now = now or time.time()
    dead = [k for k, exp in _SEEN_IDS.items() if exp <= now]
    for k in dead:
        _SEEN_IDS.pop(k, None)

def canon_id_for_capsule(topic: str, capsule: Dict[str, Any]) -> str:
    """
    Produce a stable id for a capsule on a topic.
    For voice_frame we avoid hashing the entire base64 by using a short fingerprint.
    """
    c = dict(capsule)  # shallow copy
    try:
        if "voice_frame" in c:
            vf = dict(c["voice_frame"])
            b64 = vf.get("data_b64") or vf.get("bytes_b64") or vf.get("b64") or ""
            vf["b64_len"]  = len(b64)
            vf["b64_head"] = b64[:12]
            vf["b64_tail"] = b64[-12:]
            vf.pop("data_b64", None)
            vf.pop("bytes_b64", None)
            vf.pop("b64", None)
            c["voice_frame"] = vf
    except Exception:
        pass

    payload = json.dumps({"t": topic, "c": c}, sort_keys=True, separators=(",", ":"))
    return "msg_" + hashlib.sha1(payload.encode("utf-8")).hexdigest()

def already_seen(msg_id: str) -> bool:
    now = time.time()
    with _SEEN_LOCK:
        _seen_prune(now)
        exp = _SEEN_IDS.get(msg_id)
        return bool(exp and exp > now)

def mark_seen(msg_id: str, ttl: float = _SEEN_TTL_SEC) -> None:
    with _SEEN_LOCK:
        _SEEN_IDS[msg_id] = time.time() + ttl


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
    """
    GlyphNet TX:
      • Auth + ACL
      • entanglement_lock passthrough (no de-dup here; LOCKS handles state)
      • voice_frame/text capsules:
          - compute canonical msg_id
          - drop duplicates within TTL
          - publish envelope WITH `id`
          - return ACK { msg_id, duplicate, delivered }
    """
    # --- Auth gate (dev-token allowed if env toggled) ---
    token = _extract_token(request, payload)
    if not (_dev_token_allows(token) or (token and validate_agent_token(token))):
        raise HTTPException(status_code=401, detail="Unauthorized (invalid or missing token)")

    recipient = payload.get("recipient") or payload.get("topic")
    capsule   = payload.get("capsule") or {}
    meta: Dict[str, Any] = payload.get("meta") or {}

        # --- Basic size guards for text/glyph capsules ---
    cap = capsule if isinstance(capsule, dict) else {}

    # too many tokens in one shot
    if isinstance(cap.get("glyphs"), list) and len(cap["glyphs"]) > MAX_GLYPHS:
        return JSONResponse(
            {"ok": False, "error": "too many glyphs", "max": MAX_GLYPHS},
            status_code=413
        )

    # (optional) guard streamed chunks count too
    if isinstance(cap.get("glyph_stream"), list) and len(cap["glyph_stream"]) > MAX_GLYPHS:
        return JSONResponse(
            {"ok": False, "error": "glyph_stream too large", "max": MAX_GLYPHS},
            status_code=413
        )

    # legacy plaintext text guard (if still accepted anywhere)
    txt = cap.get("text")
    if isinstance(txt, str) and len(txt) > MAX_TEXT_LEN:
        return JSONResponse(
            {"ok": False, "error": "text too large", "max": MAX_TEXT_LEN},
            status_code=413
        )

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

    # ============================================================
    # 1) entanglement_lock (PTT floor control)
    # ============================================================
    lock = (capsule or {}).get("entanglement_lock")
    if lock is not None:
        op       = (lock.get("op") or "acquire").lower()
        resource = lock.get("resource") or f"voice:{recipient}"  # default to ucs:// recipient
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

        try:
            from backend.routes.ws.glyphnet_ws import broadcast_event_throttled as broadcast_json  # type: ignore
            broadcast_json({**lock_event, "topic": topic})
        except Exception:
            pass

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

    # ============================================================
    # 2) voice_frame
    # ============================================================
    if "voice_frame" in capsule:
        try:
            vf = VoiceFrame(**capsule["voice_frame"])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"invalid voice_frame: {e}")

        # Local soft gate to avoid talk-over
        busy_reason = _soft_acquire(vf.channel, agent_id)
        if busy_reason:
            return {"status": "busy", "reason": busy_reason, "channel": vf.channel, "seq": vf.seq}

        # Canonical ID + de-dup
        vf_caps = {"voice_frame": vf.dict()}
        msg_id  = canon_id_for_capsule(topic, vf_caps)
        if already_seen(msg_id):
            return {
                "status": "ok",
                "kind": "voice_frame",
                "delivered": 0,
                "duplicate": True,
                "channel": vf.channel,
                "seq": vf.seq,
                "topic": topic,
                "msg_id": msg_id,
            }
        mark_seen(msg_id)

        env = {
            "id": msg_id,                           # ← IMPORTANT: stable id
            "type": "glyphnet_voice_frame",
            "recipient": recipient,
            "capsule": vf_caps,
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
            "duplicate": False,
            "channel": vf.channel,
            "seq": vf.seq,
            "lock_until": until,
            "topic": topic,
            "msg_id": msg_id,
        }

    if "voice_note" in capsule:
        vn = capsule["voice_note"] or {}
        # expect: { ts, mime, data_b64 }
        try:
            ts = int(vn.get("ts") or time.time() * 1000)
            mime = str(vn.get("mime") or "audio/webm")
            data_b64 = str(vn.get("data_b64") or vn.get("bytes_b64") or vn.get("b64") or "")
            if not data_b64:
                raise ValueError("missing data_b64")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"invalid voice_note: {e}")

        vn_caps = {"voice_note": {"ts": ts, "mime": mime, "data_b64": data_b64}}
        msg_id  = canon_id_for_capsule(topic, vn_caps)
        if already_seen(msg_id):
            return {"status":"ok","kind":"voice_note","delivered":0,"duplicate":True,"topic":topic,"msg_id":msg_id}
        mark_seen(msg_id)

        env = {
            "id": msg_id,
            "type": "glyphnet_voice_note",
            "recipient": recipient,
            "capsule": vn_caps,
            "meta": meta,
            "sender": agent_id,
            "ts": ts,
        }

        try:
            delivered = await glyph_bus.publish(topic, env)
        except Exception as e:
            logger.error(f"[GlyphNetTX] bus.publish (voice_note) error: {e}")
            delivered = 0
        if not delivered:
            try:
                delivered = await fanout_bus_envelope(topic, env)
            except Exception:
                pass

        try:
            log_thread_event(topic, {
                "graph": graph,
                "type": "voice",
                "ts": time.time(),
                "from": agent_id,
                "to": recipient,
                "payload": {"mime": mime, "bytes_b64": data_b64[:24] + "..."},
            }, direction="out", user_id=agent_id)
        except Exception:
            pass

        return {"status":"ok","kind":"voice_note","delivered":int(delivered or 0),"duplicate":False,"topic":topic,"msg_id":msg_id}
    

    # ============================================================
    # 3) text capsules (glyphs / glyph_stream)
    # ============================================================
    if not (capsule.get("glyphs") or capsule.get("glyph_stream")):
        raise HTTPException(status_code=400, detail="capsule must contain glyphs/glyph_stream or voice_frame")

    try:
        validate_photon_capsule(capsule)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid photon capsule: {e}")

    # Canonical ID + de-dup
    msg_id = canon_id_for_capsule(topic, capsule)
    if already_seen(msg_id):
        return {
            "status": "ok",
            "kind": "capsule",
            "delivered": 0,
            "duplicate": True,
            "topic": topic,
            "msg_id": msg_id,
        }
    mark_seen(msg_id)

    # Build envelope (ensure our canonical id is present)
    env = envelope_capsule(recipient, capsule, meta)
    env["id"] = msg_id                     # ← force canonical id
    env.setdefault("type", "glyphnet_capsule")
    env.setdefault("ts", int(time.time() * 1000))

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

    return {
        "status": "ok",
        "kind": "capsule",
        "delivered": int(delivered or 0),
        "duplicate": False,
        "topic": topic,
        "msg_id": msg_id,
    }
    
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