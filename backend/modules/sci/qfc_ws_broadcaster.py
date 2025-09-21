# File: backend/modules/sci/qfc_ws_broadcaster.py
import time
import asyncio
from typing import Dict, Any, Optional
from backend.modules.codex.codex_websocket_interface import send_codex_ws_event

DEFAULT_QFC_BROADCAST_EVENT = "qfc_field_update"

async def broadcast_qfc_state(
    field_state: Dict[str, Any],
    observer_id: Optional[str] = None,
    event_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Broadcasts the current Quantum Field Canvas (QFC) state over WebSocket.
    Triggered by replay ticks, field mutations, plugins, or manual interactions.

    Args:
        field_state: Current state of the QFC field (nodes, links, glyphs, etc.).
        observer_id: Optional identifier for the observer or HUD.
        event_type: Optional override for event name (default is "qfc_field_update").
        metadata: Optional additional metadata to include in the broadcast.
    """
    payload = {
        "event": event_type or DEFAULT_QFC_BROADCAST_EVENT,
        "data": {
            "observer_id": observer_id or "anonymous",
            "nodes": field_state.get("nodes", []),
            "links": field_state.get("links", []),
            "glyphs": field_state.get("glyphs", []),
            "scrolls": field_state.get("scrolls", []),
            "qwaveBeams": field_state.get("qwaveBeams", []),
            "entanglement": field_state.get("entanglement", {}),
            "sqi_metrics": field_state.get("sqi_metrics", {}),
            "camera": field_state.get("camera", {}),
            "tags": field_state.get("reflection_tags", []),
        }
    }

    # Inject metadata if provided
    if metadata:
        payload["data"]["metadata"] = metadata

    try:
        await send_codex_ws_event(payload)
        print(f"📡 Broadcasted QFC field update for observer: {observer_id or 'anonymous'}")
    except Exception as e:
        print(f"❌ Failed to broadcast QFC field update: {e}")

async def broadcast_qfc_tick_update(
    tick_id: int,
    frame_state: Dict[str, Any],
    observer_id: Optional[str] = None,
    total_ticks: Optional[int] = None,
    source: Optional[str] = None
):
    """
    Broadcasts a single QFC tick/frame update during symbolic replay or Codex execution.
    Designed for GHX Timeline, QWave replays, collapse tracing, etc.

    Args:
        tick_id: Current tick/frame number.
        frame_state: State of the QFC field at this tick (nodes, links, beams, etc.).
        observer_id: Optional HUD or agent ID viewing the replay.
        total_ticks: Optional total number of ticks (for HUD progress tracking).
        source: Optional identifier for what triggered the broadcast (e.g., "GHXReplay", "plugin.sqi").
    """
    metadata = {
        "tick": tick_id,
        "total_ticks": total_ticks,
        "source": source or "replay",
        "timestamp": time.time()
    }

    await broadcast_qfc_state(
        field_state=frame_state,
        observer_id=observer_id,
        event_type="qfc_sync_tick",
        metadata=metadata
    )