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

import asyncio
import logging
from fastapi import WebSocket
from typing import Dict, List, Any, Optional

from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.state.state_manager import state_manager
from backend.modules.prediction.predictive_glyph_composer import PredictiveGlyphComposer
from backend.modules.glyphnet.agent_identity_registry import agent_identity_registry
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter, crdt_registry

logger = logging.getLogger(__name__)

# Connected clients
active_connections: List[WebSocket] = []

# Broadcast queue
event_queue: asyncio.Queue = asyncio.Queue()

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

# ✅ Broadcast Event Enqueue
async def broadcast_event(event: Dict[str, Any]):
    """Enqueue a symbolic event for broadcast."""
    await event_queue.put(event)

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
    await broadcast_event({
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
    await broadcast_event(payload)
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
            await broadcast_event({
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

# ✅ Lock Overlay Broadcast
async def broadcast_lock_overlay(state: str, target_id: str, agent_id: str):
    event_type = "entanglement_lock_acquired" if state == "acquired" else "entanglement_lock_released"
    await broadcast_event({
        "type": event_type,
        "target_id": target_id,
        "agent_id": agent_id,
        "tags": ["↔", "🔒"]
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