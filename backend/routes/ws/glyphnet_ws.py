"""
📡 glyphnet_ws.py

🛰️ GlyphNet WebSocket Dispatcher for AION & Symbolic Systems
Handles real-time streaming of glyph activity, entanglement, SoulLaw verdicts, and symbolic future paths.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔮 Symbolic Broadcast Engine – Design Rubric
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
import time
import asyncio
import logging
from fastapi import APIRouter, WebSocket
from typing import Dict, List, Any, Optional

from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.prediction.predictive_glyph_composer import PredictiveGlyphComposer
from backend.modules.glyphnet.agent_identity_registry import agent_identity_registry
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter, crdt_registry
from backend.modules.glyphnet.broadcast_throttle import install, throttled_broadcast
from backend.modules.teleport.portal_manager import PORTALS, create_teleport_packet
from backend.modules.consciousness.state_manager import STATE


logger = logging.getLogger(__name__)

# Connected clients
active_connections: List[WebSocket] = []

# Broadcast queue
event_queue: asyncio.Queue = asyncio.Queue()

# --- FastAPI router + endpoint so main.py can include_router(...) ---
router = APIRouter()

_loop_started = False  # make sure the background broadcaster is started once

@router.websocket("/ws/glyphnet")
async def glyphnet_websocket_endpoint(websocket: WebSocket):
    """
    Public WS endpoint:
      - accepts the connection
      - ensures the broadcast loop is running
      - receives JSON messages and pipes them to handle_glyphnet_event
      - cleans up on disconnect
    """
    global _loop_started

    await websocket.accept()
    active_connections.append(websocket)

    # Start background broadcast loop once
    if not _loop_started:
        start_glyphnet_ws_loop()
        _loop_started = True

    # optional hello (safe to keep)
    try:
        await websocket.send_json({"type": "status", "message": "🛰️ Connected to GlyphNet WebSocket"})
    except Exception:
        # ignore initial send errors
        pass

    try:
        while True:
            msg = await websocket.receive_json()
            await handle_glyphnet_event(websocket, msg)
    except Exception:
        # client closed or bad frame; fall through to cleanup
        pass
    finally:
        disconnect(websocket)

# ✅ Connection Handling
async def connect(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    await websocket.send_json({
        "type": "status",
        "message": "🛰️ Connected to GlyphNet WebSocket"
    })
    logger.info(f"WebSocket connected: {websocket.client}")

def disconnect(websocket: WebSocket):
    if websocket in active_connections:
        active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected: {websocket.client}")

def emit_websocket_event(event_type: str, data: dict):
    """
    Emit a generic event to all WebSocket clients.
    """
    payload = {
        "type": event_type,
        "data": data
    }
    for ws in connected_clients:
        try:
            asyncio.ensure_future(ws.send_json(payload))
        except Exception as e:
            logger.warning(f"[WebSocket] Failed to emit event to client: {e}")

# ✅ Broadcast Event Enqueue
async def broadcast_event(event: Dict[str, Any]):
    """Enqueue a symbolic event for broadcast."""
    await event_queue.put(event)

install(broadcast_event)

# Fire-and-forget, throttled alias for high-volume callers
def broadcast_event_throttled(event: Dict[str, Any]) -> None:
    # non-awaiting; lets the throttle coalesce bursts
    throttled_broadcast(event)

# ✅ Background Broadcast Loop
async def glyphnet_ws_loop():
    """Async loop that dispatches queued events to all connected clients."""
    while True:
        event = await event_queue.get()
        disconnected = []
        for conn in active_connections:
            try:
                await conn.send_json(event)
            except Exception as e:
                logger.warning(f"WebSocket send error: {e}")
                disconnected.append(conn)
        for conn in disconnected:
            disconnect(conn)

def start_glyphnet_ws_loop():
    """Start the background broadcast loop."""
    asyncio.create_task(glyphnet_ws_loop())

# ─────────────────────────────────────────────────────────────────────────────
# Throttled broadcast adapter (prevents event floods)
# Place right after start_glyphnet_ws_loop()
# ─────────────────────────────────────────────────────────────────────────────
try:
    from backend.modules.glyphnet.broadcast_throttle import install, throttled_broadcast
except Exception:
    # Soft-fallback if throttle module isn't present yet
    def install(_):  # no-op
        pass
    def throttled_broadcast(event: dict):
        # naive passthrough if throttle unavailable
        asyncio.create_task(broadcast_event(event))

# Bridge the throttler (which expects a sender) to our enqueue-based API.
# Our broadcast_event accepts a *single event dict*. We pass it through.
def _throttle_sender(event: dict):
    # Use the existing enqueue path
    asyncio.create_task(broadcast_event(event))

# Register our sender with the throttle module
install(_throttle_sender)

# Export a throttled alias others can import and call with a dict.
def broadcast_event_throttled(event: dict):
    """
    Throttled version of broadcast_event(event_dict).
    Use this in high-volume code paths (e.g., large container loads, atom loops).
    """
    throttled_broadcast(event)

# ✅ Agent Identity Handshake
async def handle_agent_identity_register(websocket: WebSocket, msg: Dict[str, Any]):
    """Handle agent identity registration and broadcast."""
    name = msg.get("name")
    public_key = msg.get("public_key")
    if not name or not public_key:
        await websocket.send_json({"type": "error", "message": "Missing name or public_key"})
        return

    agent_id = agent_identity_registry.register_agent(name=name, public_key=public_key)
    agent_data = agent_identity_registry.get_agent(agent_id)

    # Confirm registration to requester
    await websocket.send_json({
        "type": "agent_registered",
        "agent": agent_data,
        "agent_id": agent_id
    })

    # Broadcast agent presence to all
    broadcast_event_throttled({
        "type": "agent_joined",
        "agent": agent_data,
        "tags": ["🌐", "🤝"]
    })

# ✅ Permission Update Broadcast (🔑)
async def broadcast_permission_update(agent_id: str, glyph_id: Optional[str] = None, permission: Optional[str] = None):
    """Push permission updates to GHXVisualizer."""
    agent_state = agent_identity_registry.get_agent(agent_id)
    payload = {
        "type": "glyph_permission_update",
        "agent_id": agent_id,
        "permissions": agent_state.get("permissions", []),
        "color": agent_state.get("color"),
        "tags": ["🔑", "🛰️"]
    }
    if glyph_id and permission:
        payload.update({"glyph_id": glyph_id, "permission": permission})
    broadcast_event_throttled(payload)
    logger.info(f"[GlyphNetWS] Broadcasted glyph_permission_update for {agent_id} (glyph={glyph_id or 'all'})")

# ✅ Incoming WebSocket Event Handler
async def handle_glyphnet_event(websocket: WebSocket, msg: Dict[str, Any]):
    event_type = msg.get("event")

    # 🔹 Glyph Trigger Event
    if event_type == "trigger_glyph":
        coords = msg.get("payload", {}).get("coord", "0,0,0")
        x, y, z = map(int, coords.split(","))
        container_id = msg.get("payload", {}).get("container", "default")
        executor = GlyphExecutor(state_manager)
        await executor.trigger_glyph_remotely(container_id=container_id, x=x, y=y, z=z, source="ws_trigger")

    # 🔮 Predictive Fork Request (A7a)
    elif event_type == "predictive_forks_request":
        payload = msg.get("payload", {})
        composer = PredictiveGlyphComposer(payload["container_id"])
        predictions = await composer.compose_forward_forks(
            current_glyph=payload["glyph"],
            goal=payload.get("goal"),
            emotion=payload.get("emotion")
        )
        await websocket.send_json({
            "type": "predictive_forks_response",
            "status": "ok",
            "count": len(predictions),
            "predictions": predictions
        })

    # 🌀 Electron-triggered teleport to container
    elif event_type == "teleport_to_container":
        target_cid = msg.get("cid")
        source_cid = msg.get("source_cid")  # optional
        from backend.modules.consciousness.state_manager import STATE
        from backend.modules.teleport.portal_manager import PORTALS, create_teleport_packet
        import time

        if not target_cid:
            await websocket.send_json({ "error": "Missing target container ID" })
            return

        # Register portal and teleport packet
        portal_id = PORTALS.register_portal(source=source_cid or "unknown", target=target_cid)
        packet = create_teleport_packet(
            portal_id=portal_id,
            container_id=source_cid or "unknown",
            payload={
                "teleport_reason": "electron_click",
                "timestamp": time.time(),
                "trigger": "GHX"
            }
        )

        success = PORTALS.teleport(packet)

        await websocket.send_json({
            "type": "teleport_result",
            "portal_id": portal_id,
            "target": target_cid,
            "success": success
        })

    # 🌐 Agent Identity Registration (A8a)
    elif event_type == "agent_identity_register":
        await handle_agent_identity_register(websocket, msg)

    # 🔑 Permission Assignment/Revocation (A8d)
    elif event_type == "update_agent_permission":
        agent_id = msg.get("agent_id")
        permission = msg.get("permission")
        action = msg.get("action", "assign")
        if action == "assign":
            agent_identity_registry.assign_permission(agent_id, permission)
        else:
            agent_identity_registry.revoke_permission(agent_id, permission)
        await broadcast_permission_update(agent_id)

    # 📝 CRDT Glyph Update (A8b)
    elif event_type == "glyph_update":
        payload = msg.get("payload", {})
        glyph_id = payload.get("glyph_id")
        updates = payload.get("updates", {})
        agent_id = payload.get("agent_id", "anonymous")
        version_vector = payload.get("version_vector", {})

        kg_writer = KnowledgeGraphWriter()
        try:
            updated_glyph = kg_writer.merge_edit(
                glyph_id=glyph_id, updates=updates, agent_id=agent_id, version_vector=version_vector
            )
            broadcast_event_throttled({
                "type": "glyph_updated",
                "glyph_id": glyph_id,
                "updates": updates,
                "agent_id": agent_id,
                "version_vector": updated_glyph.get("version_vector", {})
            })
            await broadcast_permission_update(agent_id, glyph_id=glyph_id,
                                              permission=updated_glyph.get("metadata", {}).get("permission", "read-only"))
            logger.info(f"[GlyphNetWS] CRDT merged glyph {glyph_id} from agent {agent_id}")
        except KeyError:
            await websocket.send_json({
                "type": "error",
                "message": f"Glyph {glyph_id} not found for update"
            })

    # 🔒 Entanglement Lock Request (A8b)
    elif event_type == "entanglement_lock":
        glyph_id = msg.get("glyph_id")
        agent_id = msg.get("agent_id")
        if crdt_registry.acquire_lock(glyph_id, agent_id):
            await broadcast_lock_overlay("acquired", glyph_id, agent_id)
        else:
            await websocket.send_json({
                "type": "entanglement_lock_denied",
                "glyph_id": glyph_id,
                "reason": "Locked by another agent"
            })

    # 🧠 Run Prediction + Emit logic_alert if contradiction (Step 2)
    elif event_type == "run_prediction":
        container = msg.get("container", {})
        container_id = container.get("id", "unknown")

        try:
            from backend.modules.consciousness import prediction_engine
            result = prediction_engine.run_prediction_on_container(container)

            contradiction = result.get("symbolic", {}).get("contradiction")
            if contradiction:
                emit_websocket_event(
                    event_type="logic_alert",
                    data={
                        "containerId": container_id,
                        "contradiction": True,
                        "reason": contradiction.get("reason"),
                        "score": contradiction.get("score"),
                        "suggested_rewrite": result["symbolic"].get("rewrite"),
                    }
                )
        except Exception as e:
            logger.warning(f"[GlyphNetWS] Prediction error: {e}")
            await websocket.send_json({
                "type": "logic_alert",
                "error": "prediction_failed",
                "reason": str(e)
            })

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

# ✅ Entanglement Broadcast
def push_entanglement_update(from_id: str, to_id: str,
    ghx_projection_id: Optional[str] = None,
    entangled_ids: Optional[List[str]] = None,
    signal_path: Optional[List[str]] = None,
    source_entropy: Optional[str] = None):
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
    if metadata: event["metadata"] = metadata
    asyncio.create_task(broadcast_event(event))

# ✅ SoulLaw Verdict Broadcast
def stream_soullaw_verdict(verdict: str, glyph: str, context: str = "SoulLaw"):
    try:
        payload = {
            "type": "soullaw_event",
            "verdict": verdict,
            "glyph": glyph,
            "context": context,
            "tags": ["⚖️", "🔒"] if verdict == "violation" else ["⚖️", "✅"]
        }
        asyncio.create_task(broadcast_event(payload))
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
                    "reasoning": pred.get("reasoning")
                }
            }
            asyncio.create_task(broadcast_event(event))
        logger.info(f"[GlyphNetWS] Streamed {len(predictions)} prediction paths.")
    except Exception as e:
        logger.warning(f"[GlyphNetWS] Failed to stream prediction paths: {e}")

# ✅ Cross-Agent KG Fusion Broadcast
def fusion_broadcast(node_id: str, confidence: float, entropy: float, source_agent: str,
    entangled_nodes: Optional[List[str]] = None, tags: Optional[List[str]] = None):
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