"""
📡 glyphnet_ws.py

🛰️ GlyphNet WebSocket Dispatcher for AION & Symbolic Systems
Handles real-time streaming of glyph activity, entanglement, SoulLaw verdicts, and symbolic future paths.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔮 Symbolic Broadcast Engine - Design Rubric
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Real-Time Glyph Trigger Streaming
✅ ↔ Entanglement & QGlyph Metadata Sync
✅ SoulLaw Verdict Push (⚖️ 🔒 ✅)
✅ Prediction Path Broadcast (🔮 ↗ 🛤️)
✅ WebSocket + Agent Broadcast Hooks
✅ CRDT Merge + Entanglement Lock Sync
✅ Replay Integration & GHX Embedding Ready
✅ Dream Match + Cost Trace Support
✅ Ethical Signal Injection & Confidence Tags
✅ Live Permission Diff + Identity Color Sync (NEW)
"""
from __future__ import annotations
import os
import time
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from copy import deepcopy

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.prediction.predictive_glyph_composer import PredictiveGlyphComposer
from backend.modules.glyphnet.agent_identity_registry import agent_identity_registry
from backend.modules.knowledge_graph.crdt_registry_singleton import get_crdt_registry
from backend.modules.teleport.portal_manager import PORTALS, create_teleport_packet
from backend.modules.consciousness.state_manager import STATE
from backend.modules.websocket_manager import send_ws_message
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.glyphnet.agent_identity_registry import validate_agent_token

kg_writer = get_kg_writer()
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from backend.modules.symbolic_engine.math_logic_kernel import LogicGlyph

# Broadcast queue (typed)
event_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

# FastAPI router
router = APIRouter()

# Ensure we only boot the broadcaster once
_loop_started = False

# Connected clients + (optional) topic subscription
active_connections: List[WebSocket] = []

# Optional per-socket topic subscriptions (None = receive all)
subscriptions: Dict[WebSocket, Optional[str]] = {}

def _dev_token_allows(token: Optional[str]) -> bool:
    return (
        os.getenv("GLYPHNET_ALLOW_DEV_TOKEN", "0").lower() in {"1","true","yes","on"}
        and token in {"dev-token", "local-dev"}
    )

def _norm_topic(s: Optional[str]) -> str:
    if not s:
        return ""
    return s.replace("gnet:", "")


async def fanout_bus_envelope(topic: str, envelope: dict) -> int:
    """
    Deliver an envelope to all sockets subscribed to `topic`.
    Falls back to broadcast when a socket has no subscription (wildcard).
    """
    delivered = 0
    dead: List[WebSocket] = []
    norm_t = _norm_topic(topic)

    payload = {
        "type": "glyphnet_capsule",
        "topic": topic,
        "envelope": envelope,
    }

    for ws, sub in list(subscriptions.items()):
        try:
            if sub and _norm_topic(sub) != norm_t:
                continue
            await ws.send_json(payload)
            delivered += 1
        except Exception:
            dead.append(ws)

    for ws in dead:
        try:
            subscriptions.pop(ws, None)
            if ws in active_connections:
                active_connections.remove(ws)
        except Exception:
            pass
    return delivered

# -- Topic-scoped JSON broadcast (sync wrapper used by REST handlers) --
def broadcast_json(topic: str, payload: dict) -> int:
    """
    Schedule a JSON payload to all sockets subscribed to `topic`.
    Returns number of sockets targeted. Non-blocking (schedules tasks).
    """
    delivered = 0
    norm_t = _norm_topic(topic)
    dead: List[WebSocket] = []

    for ws, sub in list(subscriptions.items()):
        try:
            if sub and _norm_topic(sub) != norm_t:
                continue
            # schedule send non-blocking
            asyncio.create_task(ws.send_json(payload))
            delivered += 1
        except Exception:
            dead.append(ws)

    for ws in dead:
        try:
            subscriptions.pop(ws, None)
            if ws in active_connections:
                active_connections.remove(ws)
        except Exception:
            pass
    return delivered

@router.websocket("/ws/glyphnet")
async def glyphnet_websocket_endpoint(websocket: WebSocket):
    """
    Public WS endpoint:
      - validates identity token
      - records optional topic subscription (?topic=ucs://...)
      - runs the background broadcaster once
    """
    global _loop_started

    # 🔐 Validate BEFORE accepting
    try:
        token = websocket.query_params.get("token")
        if not (_dev_token_allows(token) or (token and validate_agent_token(token))):
            # policy violation; do not accept
            await websocket.close(code=1008)
            logger.warning(f"[GlyphNetWS] ❌ Unauthorized connection attempt: {websocket.client}")
            return
    except Exception as e:
        logger.error(f"[GlyphNetWS] Token validation error: {e}")
        await websocket.close(code=1011)
        return

    # ✅ Authorized — accept and register
    await websocket.accept()
    active_connections.append(websocket)
    subscriptions[websocket] = websocket.query_params.get("topic")

    if not _loop_started:
        start_glyphnet_ws_loop()
        _loop_started = True

    try:
        await websocket.send_json({"type": "status", "message": "🛰️ Connected to GlyphNet WebSocket"})
    except Exception:
        pass

    try:
        while True:
            msg = await websocket.receive_json()
            await handle_glyphnet_event(websocket, msg)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"[GlyphNetWS] receive loop error: {e}")
    finally:
        # clean disconnect
        try:
            active_connections.remove(websocket)
        except Exception:
            pass
        subscriptions.pop(websocket, None)
        logger.info(f"[GlyphNetWS] WebSocket disconnected: {websocket.client}")


def disconnect(websocket: WebSocket):
    # keep a single source of truth for removal
    try:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception:
        pass
    subscriptions.pop(websocket, None)
    logger.info(f"[GlyphNetWS] WebSocket disconnected: {websocket.client}")


def emit_websocket_event(event_type: str, data: dict):
    """
    Emit a generic event to all WebSocket clients.
    """
    payload = {"type": event_type, "data": data}
    for ws in list(active_connections):
        try:
            asyncio.ensure_future(ws.send_json(payload))
        except Exception as e:
            logger.warning(f"[WebSocket] Failed to emit event to client: {e}")


# ✅ Broadcast Event Enqueue
async def broadcast_event(event: Dict[str, Any]):
    """Enqueue a symbolic event for broadcast."""
    # copy to avoid caller-side mutation after enqueue
    await event_queue.put(deepcopy(event))


# ✅ Background Broadcast Loop
async def glyphnet_ws_loop():
    """Async loop that dispatches queued events to all connected clients."""
    while True:
        event = await event_queue.get()
        disconnected: List[WebSocket] = []
        for conn in list(active_connections):
            try:
                await conn.send_json(event)
            except Exception as e:
                logger.warning(f"[GlyphNetWS] send error: {e}")
                disconnected.append(conn)
        for conn in disconnected:
            disconnect(conn)


def start_glyphnet_ws_loop():
    """Start the background broadcast loop."""
    asyncio.create_task(glyphnet_ws_loop())


# ─────────────────────────────────────────────────────────────────────────────
# Throttled broadcast adapter (prevents event floods)
# ─────────────────────────────────────────────────────────────────────────────
try:
    # Alias to avoid colliding with our local names
    from backend.modules.glyphnet.broadcast_throttle import (
        install as throttle_install,
        throttled_broadcast,
    )
except Exception:
    # Soft-fallback if throttle module isn't present yet
    async def throttled_broadcast(event: dict):
        await broadcast_event(event)

    def throttle_install(_sender):
        # no-op
        return


# Bridge the throttler (which expects a sender) to our enqueue-based API.
def _throttle_sender(event: dict):
    asyncio.create_task(broadcast_event(event))


# Register our sender with the throttle module (once, at import time)
throttle_install(_throttle_sender)


# Public throttled alias for high-volume callers
def broadcast_event_throttled(event: Dict[str, Any]) -> None:
    """
    Throttled version of broadcast_event(event_dict).
    Use this in high-volume code paths (e.g., large container loads, atom loops).
    """
    # NOTE: throttled_broadcast may be async or sync depending on implementation.
    res = throttled_broadcast(event)
    if asyncio.iscoroutine(res):
        asyncio.create_task(res)


# ✅ Agent Identity Handshake
async def handle_agent_identity_register(websocket: WebSocket, msg: Dict[str, Any]):
    """Handle agent identity registration and broadcast."""
    name = msg.get("name")
    public_key = msg.get("public_key")
    if not name or not public_key:
        await websocket.send_json(
            {"type": "error", "message": "Missing name or public_key"}
        )
        return

    agent_id = agent_identity_registry.register_agent(
        name=name, public_key=public_key
    )
    agent_data = agent_identity_registry.get_agent(agent_id)

    # Confirm registration to requester
    await websocket.send_json(
        {"type": "agent_registered", "agent": agent_data, "agent_id": agent_id}
    )

    # Broadcast agent presence to all
    broadcast_event_throttled(
        {"type": "agent_joined", "agent": agent_data, "tags": ["🌐", "🤝"]}
    )


# ✅ Permission Update Broadcast (🔑)
async def broadcast_permission_update(
    agent_id: str, glyph_id: Optional[str] = None, permission: Optional[str] = None
):
    """Push permission updates to GHXVisualizer."""
    agent_state = agent_identity_registry.get_agent(agent_id)
    payload = {
        "type": "glyph_permission_update",
        "agent_id": agent_id,
        "permissions": agent_state.get("permissions", []),
        "color": agent_state.get("color"),
        "tags": ["🔑", "🛰️"],
    }
    if glyph_id and permission:
        payload.update({"glyph_id": glyph_id, "permission": permission})
    broadcast_event_throttled(payload)
    logger.info(
        f"[GlyphNetWS] Broadcasted glyph_permission_update for {agent_id} (glyph={glyph_id or 'all'})"
    )


# ✅ Glyph Packet Log Broadcast
async def broadcast_glyph_log(
    node: str, glyph: str, status: str = "ok", message: Optional[str] = None
):
    """
    Push a glyph log entry to all connected WebSocket clients.
    Compatible with GlyphNetDebugger frontend.
    """
    event = {
        "type": "glyph_packet",
        "log": {
            "node": node,
            "glyph": glyph,
            "status": status,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }
    await broadcast_event(event)


# ✅ Incoming WebSocket Event Handler
async def handle_glyphnet_event(websocket: WebSocket, msg: Dict[str, Any]):
    event_type = msg.get("event")

    # 🔹 Glyph Trigger Event
    if event_type == "trigger_glyph":
        coords = msg.get("payload", {}).get("coord", "0,0,0")
        try:
            x, y, z = map(int, coords.split(","))
        except Exception:
            await websocket.send_json(
                {"type": "error", "message": "Bad coord format, expected 'x,y,z'"}
            )
            return
        container_id = msg.get("payload", {}).get("container", "default")
        # FIX: use STATE (imported) instead of undefined state_manager
        executor = GlyphExecutor(STATE)
        await executor.trigger_glyph_remotely(
            container_id=container_id, x=x, y=y, z=z, source="ws_trigger"
        )
        await broadcast_glyph_log(
            node="GlyphNetWS",
            glyph=f"{container_id}:{x},{y},{z}",
            status="ok",
            message="Glyph triggered remotely",
        )

    # 🔮 Predictive Fork Request (A7a)
    elif event_type == "predictive_forks_request":
        payload = msg.get("payload", {})
        composer = PredictiveGlyphComposer(payload.get("container_id"))
        predictions = await composer.compose_forward_forks(
            current_glyph=payload.get("glyph"),
            goal=payload.get("goal"),
            emotion=payload.get("emotion"),
        )
        await websocket.send_json(
            {
                "type": "predictive_forks_response",
                "status": "ok",
                "count": len(predictions),
                "predictions": predictions,
            }
        )

    # 🌀 Electron-triggered teleport to container
    elif event_type == "teleport_to_container":
        target_cid = msg.get("cid")
        source_cid = msg.get("source_cid")  # optional

        if not target_cid:
            await websocket.send_json(
                {"type": "error", "message": "Missing target container ID"}
            )
            return

        # Register portal and teleport packet
        portal_id = PORTALS.register_portal(
            source=source_cid or "unknown", target=target_cid
        )
        packet = create_teleport_packet(
            portal_id=portal_id,
            container_id=source_cid or "unknown",
            payload={"teleport_reason": "electron_click", "timestamp": time.time(), "trigger": "GHX"},
        )

        success = PORTALS.teleport(packet)

        await websocket.send_json(
            {"type": "teleport_result", "portal_id": portal_id, "target": target_cid, "success": success}
        )
    # 🌐 Agent Identity Registration (A8a)
    elif event_type == "agent_identity_register":
        await handle_agent_identity_register(websocket, msg)

    # 🔑 Permission Assignment/Revocation (A8d)
    elif event_type == "update_agent_permission":
        agent_id = msg.get("agent_id")
        permission = msg.get("permission")
        action = (msg.get("action") or "assign").lower()

        if not agent_id or not permission:
            await websocket.send_json({
                "type": "error",
                "error": "bad_request",
                "message": "agent_id and permission are required"
            })
            return

        try:
            if action == "assign":
                agent_identity_registry.assign_permission(agent_id, permission)
                action_out = "assigned"
            else:
                agent_identity_registry.revoke_permission(agent_id, permission)
                action_out = "revoked"

            # delivery receipt (to caller)
            await _send_delivery_receipt(
                websocket,
                event="update_agent_permission",
                ok=True,
                agent_id=agent_id,
                permission=permission,
                action=action_out,
            )

            # fanout summary (to listeners)
            await broadcast_permission_update(agent_id)

        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "error": "permission_update_failed",
                "message": str(e),
            })

    # 📝 CRDT Glyph Update (A8b)  — with per-glyph ACL & delivery receipt
    elif event_type == "glyph_update":
        payload = msg.get("payload") or {}
        glyph_id = payload.get("glyph_id")
        updates = payload.get("updates") or {}
        agent_id = payload.get("agent_id") or "anonymous"
        version_vector = payload.get("version_vector") or {}

        if not glyph_id or not isinstance(updates, dict):
            await websocket.send_json({
                "type": "error",
                "error": "bad_request",
                "message": "glyph_update requires payload.glyph_id and payload.updates{}",
            })
            return

        # ── D01 Topic ACLs (per-glyph)
        has_write = True
        try:
            # Expected shape: "glyph:<glyph_id>:write", with a coarse fallback to "glyph:write"
            perm_key_specific = f"glyph:{glyph_id}:write"
            perm_key_coarse = "glyph:write"
            has_write = (
                agent_identity_registry.has_permission(agent_id, perm_key_specific)
                or agent_identity_registry.has_permission(agent_id, perm_key_coarse)
            )
        except Exception:
            # If registry cannot be queried (dev), permit but log
            logger.debug("[GlyphNetWS] permission check skipped (dev or registry not available)")

        if not has_write:
            await websocket.send_json({
                "type": "error",
                "error": "forbidden",
                "message": f"agent '{agent_id}' lacks write permission for glyph '{glyph_id}'",
            })
            await broadcast_glyph_log(
                node="GlyphNetWS",
                glyph=glyph_id,
                status="forbidden",
                message=f"Write denied for agent {agent_id}",
            )
            return

        # ── Merge via KG writer
        from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
        kg_writer = get_kg_writer()

        try:
            updated_glyph = kg_writer.merge_edit(
                glyph_id=glyph_id,
                updates=updates,
                agent_id=agent_id,
                version_vector=version_vector,
            )

            # Fanout: mutation notice
            broadcast_event_throttled({
                "type": "glyph_updated",
                "glyph_id": glyph_id,
                "updates": updates,
                "agent_id": agent_id,
                "version_vector": updated_glyph.get("version_vector", {}),
            })

            # Bus log + permission echo (if metadata carries a new permission)
            await broadcast_glyph_log(
                node="GlyphNetWS",
                glyph=glyph_id or "[unknown]",
                status="ok",
                message=f"Glyph updated by {agent_id}",
            )
            await broadcast_permission_update(
                agent_id,
                glyph_id=glyph_id,
                permission=updated_glyph.get("metadata", {}).get("permission", "read-only"),
            )

            # ── D01 Delivery receipt (to the caller only)
            await _send_delivery_receipt(
                websocket,
                event="glyph_update",
                ok=True,
                glyph_id=glyph_id,
                agent_id=agent_id,
                version_vector=updated_glyph.get("version_vector", {}),
            )

            logger.info(f"[GlyphNetWS] CRDT merged glyph {glyph_id} from agent {agent_id}")

        except KeyError:
            await websocket.send_json({
                "type": "error",
                "error": "not_found",
                "message": f"Glyph {glyph_id} not found for update",
            })
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "error": "merge_failed",
                "message": str(e),
            })

    # 🔒 Entanglement Lock Request (A8b)
    elif event_type == "entanglement_lock":
        glyph_id = msg.get("glyph_id")
        agent_id = msg.get("agent_id") or "anonymous"

        if not glyph_id:
            await websocket.send_json({
                "type": "error",
                "error": "bad_request",
                "message": "glyph_id is required for entanglement_lock",
            })
            return

        from backend.modules.knowledge_graph.crdt_registry_singleton import get_crdt_registry
        crdt_registry = get_crdt_registry()

        granted = crdt_registry.acquire_lock(glyph_id, agent_id)
        if granted:
            await broadcast_glyph_log(
                node="GlyphNetWS",
                glyph=glyph_id,
                status="ok",
                message=f"Entanglement lock acquired by {agent_id}",
            )
            await broadcast_lock_overlay("acquired", glyph_id, agent_id)
            await _send_delivery_receipt(
                websocket,
                event="entanglement_lock",
                ok=True,
                glyph_id=glyph_id,
                agent_id=agent_id,
                state="acquired",
            )
        else:
            await websocket.send_json({
                "type": "entanglement_lock_denied",
                "glyph_id": glyph_id,
                "reason": "Locked by another agent",
            })
            await _send_delivery_receipt(
                websocket,
                event="entanglement_lock",
                ok=False,
                glyph_id=glyph_id,
                agent_id=agent_id,
                state="denied",
            )

    # 🧠 Run Prediction + Emit logic_alert if contradiction (Step 2)
    elif event_type == "run_prediction":
        container = msg.get("container") or {}
        container_id = container.get("id") or "unknown"

        try:
            from backend.modules.consciousness import prediction_engine
            result = prediction_engine.run_prediction_on_container(container)

            contradiction = (result.get("symbolic") or {}).get("contradiction")
            if contradiction:
                emit_websocket_event(
                    event_type="logic_alert",
                    data={
                        "containerId": container_id,
                        "contradiction": True,
                        "reason": contradiction.get("reason"),
                        "score": contradiction.get("score"),
                        "suggested_rewrite": (result.get("symbolic") or {}).get("rewrite"),
                    },
                )

            # Delivery receipt back to caller with a tiny summary
            await _send_delivery_receipt(
                websocket,
                event="run_prediction",
                ok=True,
                container_id=container_id,
                contradiction=bool(contradiction),
            )

        except Exception as e:
            logger.warning(f"[GlyphNetWS] Prediction error: {e}")
            await websocket.send_json({
                "type": "logic_alert",
                "error": "prediction_failed",
                "reason": str(e),
            })
            await _send_delivery_receipt(
                websocket,
                event="run_prediction",
                ok=False,
                container_id=container_id,
                error=str(e),
            )

# ─────────────────────────────────────────────────────────────────────────────
# ✅ Lock Overlay Broadcast
async def broadcast_lock_overlay(state: str, target_id: str, agent_id: str):
    event_type = "entanglement_lock_acquired" if state == "acquired" else "entanglement_lock_released"
    broadcast_event_throttled({
        "type": event_type,
        "target_id": target_id,
        "agent_id": agent_id,
        "tags": ["↔", "🔒"],
    })
    logger.info(f"[GlyphNetWS] Broadcasted {event_type} for {target_id} by {agent_id}")

# ─────────────────────────────────────────────────────────────────────────────
# ✅ Delivery receipt helper (D01)
async def _send_delivery_receipt(ws, event: str, ok: bool, **fields):
    try:
        import time as _t
        payload = {
            "type": "delivery_receipt",
            "event": event,
            "ok": bool(ok),
            "ts": _t.time(),
        }
        if "id" in fields and fields["id"] is None:
            fields.pop("id", None)
        payload.update({k: v for k, v in fields.items() if v is not None})
        await ws.send_json(payload)
    except Exception as e:
        # Never fail the main flow because a receipt couldn't be sent
        logger.debug(f"[GlyphNetWS] delivery_receipt send failed: {e}")

def broadcast_symbolic_glyph(glyph: "LogicGlyph") -> None:
    """
    Broadcasts a symbolic glyph (QGlyph or otherwise) to all connected WebSocket listeners.
    Includes metadata flags and robust serialization.
    """
    try:
        if hasattr(glyph, "serialize"):
            glyph_payload = glyph.serialize()
        elif hasattr(glyph, "to_dict"):
            glyph_payload = glyph.to_dict()
        else:
            glyph_payload = str(glyph)

        payload = {
            "type": "symbolic_glyph",
            "id": getattr(glyph, "metadata", {}).get("id", None),
            "qglyph": getattr(glyph, "metadata", {}).get("qglyph", False),
            "entangled": getattr(glyph, "metadata", {}).get("entangled", False),
            "predictive": getattr(glyph, "metadata", {}).get("predictive", False),
            "payload": glyph_payload,
        }

        send_ws_message(json.dumps(payload))
    except Exception as e:
        logger.warning(f"Failed to broadcast symbolic glyph: {e}")

# ✅ Entanglement Broadcast
def push_entanglement_update(
    from_id: str,
    to_id: str,
    ghx_projection_id: Optional[str] = None,
    entangled_ids: Optional[List[str]] = None,
    signal_path: Optional[List[str]] = None,
    source_entropy: Optional[str] = None,
):
    event: Dict[str, Any] = {
        "type": "entanglement_update",
        "from": from_id,
        "to": to_id,
        "symbol": "↔",
    }
    metadata: Dict[str, Any] = {}
    if ghx_projection_id: metadata["ghx_projection_id"] = ghx_projection_id
    if entangled_ids: metadata["entangled_ids"] = entangled_ids
    if signal_path: metadata["signal_path"] = signal_path
    if source_entropy: metadata["source_entropy"] = source_entropy
    if metadata:
        event["metadata"] = metadata
    asyncio.create_task(broadcast_event(event))

# ✅ SoulLaw Verdict Broadcast
def stream_soullaw_verdict(verdict: str, glyph: str, context: str = "SoulLaw"):
    try:
        payload = {
            "type": "soullaw_event",
            "verdict": verdict,
            "glyph": glyph,
            "context": context,
            "tags": ["⚖️", "🔒"] if verdict == "violation" else ["⚖️", "✅"],
        }
        asyncio.create_task(broadcast_event(payload))
        asyncio.create_task(broadcast_glyph_log(
            node="SoulLaw",
            glyph=glyph,
            status=verdict,
            message=f"SoulLaw {verdict}",
        ))
        logger.info(f"[GlyphNetWS] Streamed SoulLaw {verdict}: {glyph}")
    except Exception as e:
        logger.warning(f"[GlyphNetWS] Failed to stream SoulLaw verdict: {e}")

# ✅ Prediction Path Broadcast
def stream_prediction_paths(predictions: List[Dict[str, Any]], container_path: Optional[str] = None):
    try:
        for pred in predictions:
            event = {
                "type": "prediction_path",
                "glyph": pred.get("input_glyph"),
                "predicted": pred.get("predicted_glyph"),
                "confidence": pred.get("confidence"),
                "goal": pred.get("goal"),
                "container": container_path or pred.get("container_path"),
                "tags": ["🔮", "↗", "🛤️"],
                "meta": {
                    "soul_law": pred.get("soul_law_violation"),
                    "dream_match": pred.get("is_dream_pattern"),
                    "cost": pred.get("codex_cost_estimate"),
                    "multiverse": pred.get("multiverse_label"),
                    "reasoning": pred.get("reasoning"),
                },
            }
            asyncio.create_task(broadcast_event(event))
        logger.info(f"[GlyphNetWS] Streamed {len(predictions)} prediction paths.")
    except Exception as e:
        logger.warning(f"[GlyphNetWS] Failed to stream prediction paths: {e}")

# ✅ Cross-Agent KG Fusion Broadcast
def fusion_broadcast(
    node_id: str,
    confidence: float,
    entropy: float,
    source_agent: str,
    entangled_nodes: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
):
    try:
        event: Dict[str, Any] = {
            "type": "fusion_update",
            "node": {
                "id": node_id,
                "confidence": confidence,
                "entropy": entropy,
                "source_agent": source_agent,
            },
            "entangled_nodes": entangled_nodes or [],
            "tags": tags or ["↔", "🌐"],
        }
        asyncio.create_task(broadcast_event(event))
        logger.info(f"[GlyphNetWS] Fusion broadcast: {node_id} ({confidence:.2f}) from {source_agent}")
    except Exception as e:
        logger.warning(f"[GlyphNetWS] Failed fusion_broadcast for {node_id}: {e}")

# ✅ Anchor Update Broadcast
async def broadcast_anchor_update(glyph_id: str, anchor_data: Dict[str, Any]):
    event = {
        "type": "anchor_update",
        "glyph_id": glyph_id,
        "anchor": anchor_data,
    }
    await broadcast_event(event)
    logger.info(f"[GlyphNetWS] Broadcasted anchor update for {glyph_id}: {anchor_data}")

# ✅ Replay Frame Streaming (A6a)
async def stream_replay_frame(frame_index: int, glyph_state: Dict[str, Any], container_id: str):
    event = {
        "type": "glyph_replay_frame",
        "frame_index": frame_index,
        "container_id": container_id,
        "glyph_state": glyph_state,
    }
    await broadcast_event(event)
    logger.debug(f"[GlyphNetWS] Streamed replay frame {frame_index} for container {container_id}")

# ─────────────────────────────────────────────────────────────────────────────
# ✅ Alias for backward compatibility
broadcast_glyph_event = broadcast_event_throttled