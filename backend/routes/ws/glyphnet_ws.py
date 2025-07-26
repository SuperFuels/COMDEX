import asyncio
from fastapi import WebSocket
from typing import Dict, List, Any, Optional

from backend.modules.codex.glyph_executor import GlyphExecutor
from backend.modules.state.state_manager import state_manager

# Connected clients
active_connections: List[WebSocket] = []

# Broadcast queue
event_queue: asyncio.Queue = asyncio.Queue()


async def connect(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    await websocket.send_json({
        "type": "status",
        "message": "🛰️ Connected to GlyphNet WebSocket"
    })


def disconnect(websocket: WebSocket):
    if websocket in active_connections:
        active_connections.remove(websocket)


async def broadcast_event(event: Dict[str, Any]):
    """Enqueue a symbolic event for broadcast."""
    await event_queue.put(event)


async def glyphnet_ws_loop():
    """Async loop that dispatches queued events to all connected clients."""
    while True:
        event = await event_queue.get()
        disconnected = []
        for conn in active_connections:
            try:
                await conn.send_json(event)
            except Exception:
                disconnected.append(conn)
        for conn in disconnected:
            disconnect(conn)


def start_glyphnet_ws_loop():
    """Start the background broadcast loop."""
    asyncio.create_task(glyphnet_ws_loop())


def push_entanglement_update(
    from_id: str,
    to_id: str,
    ghx_projection_id: Optional[str] = None,
    entangled_ids: Optional[List[str]] = None,
    signal_path: Optional[List[str]] = None,
    source_entropy: Optional[str] = None
):
    """Trigger a WebSocket broadcast for ↔ entanglement, with optional GHX metadata."""
    event: Dict[str, Any] = {
        "type": "entanglement_update",
        "from": from_id,
        "to": to_id,
        "symbol": "↔",
    }

    # Optional GHX / signal metadata
    metadata: Dict[str, Any] = {}
    if ghx_projection_id:
        metadata["ghx_projection_id"] = ghx_projection_id
    if entangled_ids:
        metadata["entangled_ids"] = entangled_ids
    if signal_path:
        metadata["signal_path"] = signal_path
    if source_entropy:
        metadata["source_entropy"] = source_entropy

    if metadata:
        event["metadata"] = metadata

    asyncio.create_task(broadcast_event(event))


# 🛰️ Handle incoming WebSocket events
async def handle_glyphnet_event(websocket: WebSocket, msg: Dict[str, Any]):
    if msg.get("event") == "trigger_glyph":
        coords = msg.get("payload", {}).get("coord", "0,0,0")
        x, y, z = map(int, coords.split(","))
        container_id = msg.get("payload", {}).get("container", "default")

        executor = GlyphExecutor(state_manager)
        await executor.trigger_glyph_remotely(
            container_id=container_id,
            x=x,
            y=y,
            z=z,
            source="ws_trigger"
        )