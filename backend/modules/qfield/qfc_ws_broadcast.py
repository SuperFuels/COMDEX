# File: backend/modules/qfield/qfc_ws_broadcast.py

"""
qfc_ws_broadcast.py

Handles QFC (Quantum Field Cognition) WebSocket broadcasts for live beam events,
symbolic mutations, collapses, and visualizations across the QField interface.
"""

import asyncio
import logging
from typing import Dict, Optional, Any, Union

from backend.modules.websocket_manager import send_ws_message as ws_server

logger = logging.getLogger(__name__)

# -----------------------------------------
# 🔊 General Symbolic QFC Payload Broadcast
# -----------------------------------------
def send_qfc_payload(payload: Dict[str, Any], mode: str = "live") -> None:
    """
    Broadcast a QFC payload using WebSocket.

    Args:
        payload (Dict): The symbolic payload (e.g., from build_qfc_view).
        mode (str): Broadcast mode, e.g., "live", "replay", "mutation"
    """
    try:
        payload["mode"] = mode
        asyncio.create_task(ws_server(payload, tag="qfc_payload"))
        logger.debug(f"[QFC] Payload sent: {payload}")
    except Exception as e:
        logger.warning(f"❌ QFC WebSocket broadcast failed: {e}")


# -----------------------------------------
# 🌐 Beam Event Broadcast (e.g., from SQI)
# -----------------------------------------
def broadcast_beam_event(event: Union[Dict[str, Any], Any], event_type: str = "beam_update") -> None:
    """
    Broadcasts a symbolic beam event to QField or HUD layers.

    Args:
        event (Dict | Beam): Contains the full beam structure or partial update.
        event_type (str): Optional event tag for routing (e.g., 'collapse', 'mutation')
    """
    try:
        # Handle Beam objects directly
        if not isinstance(event, dict):
            if hasattr(event, "to_dict"):
                event = event.to_dict()
            else:
                logger.error("❌ [QFC] Event is not JSON-serializable and has no .to_dict() method.")
                return

        packet = {
            "type": event_type,
            "beam_id": event.get("id") or event.get("beam_id", "unknown"),
            "timestamp": event.get("timestamp"),
            "payload": event,
        }
        asyncio.create_task(ws_server(packet, tag="qfc_beam_event"))
        logger.info(f"📡 [QFC] Beam event broadcasted: {packet['beam_id']} ({event_type})")
    except Exception as e:
        logger.error(f"❌ [QFC] Failed to broadcast beam event: {e}")