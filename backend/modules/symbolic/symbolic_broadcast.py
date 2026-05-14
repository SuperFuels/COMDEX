# backend/modules/symbolic/symbolic_broadcast.py

"""
Symbolic Broadcast Module

This module provides a standardized way to send real-time symbolic
logic events (e.g., contradictions, rewrite suggestions) to the
Codex WebSocket layer for live rendering in HUDs or trace UIs.

These events are used in:
- CodexHUD.tsx
- RuntimeGlyphTrace.tsx
- GHXVisualizer.tsx
- SQI scoring overlays
"""

from typing import Optional, Dict, Any
from backend.modules.glyphnet.broadcast_utils import broadcast_ws_event


def broadcast_glyph_event(
    event_type: str,
    glyph: str,
    container_id: str,
    coord: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Broadcast a symbolic glyph event via WebSocket.

    Args:
        event_type (str): The symbolic event type (e.g., "contradiction", "rewrite_suggestion").
        glyph (str): The glyph or logic expression involved.
        container_id (str): ID of the container where the event occurred.
        coord (str): Coordinate within the container.
        extra (dict, optional): Additional metadata to attach (e.g., confidence score, rewrite path).
    """
    payload = {
        "type": "logic_alert",
        "data": {
            "event_type": event_type,
            "glyph": glyph,
            "container_id": container_id,
            "coord": coord,
            "extra": extra or {}
        }
    }

    # 🛰️ Dispatch over /ws/codex WebSocket
    broadcast_ws_event(payload)