# ============================================================
# 📁 backend/modules/qfield/qfc_ws_broadcast.py
# ============================================================

"""
QFCWebSocketBroadcast - handles Quantum Field Cognition (QFC)
WebSocket communication for Tessaris QQC runtime.
Provides a unified class interface for live payload and beam broadcasts.
"""

import asyncio
import logging
from typing import Dict, Any, Union, Optional

from backend.modules.websocket_manager import send_ws_message as ws_server

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Function-Level Utilities (still available)
# ──────────────────────────────────────────────
def send_qfc_payload(payload: Dict[str, Any], mode: str = "live") -> None:
    """Low-level async broadcast of a QFC payload."""
    try:
        payload["mode"] = mode
        asyncio.create_task(ws_server(payload, tag="qfc_payload"))
        logger.debug(f"[QFC] Payload sent: {payload}")
    except Exception as e:
        logger.warning(f"❌ QFC WebSocket broadcast failed: {e}")


def broadcast_beam_event(event: Union[Dict[str, Any], Any], event_type: str = "beam_update") -> None:
    """Low-level async broadcast of a beam or symbolic event."""
    try:
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


# ──────────────────────────────────────────────
#  Class Wrapper for QQC Integration
# ──────────────────────────────────────────────
class QFCWebSocketBroadcast:
    """
    Class wrapper providing start/stop lifecycle and unified broadcast interface
    for the Tessaris Quantum Quad Core runtime.
    """

    def __init__(self):
        self.active: bool = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        logger.info("[QFCWebSocketBroadcast] Initialized broadcast handler.")

    def start(self):
        """Mark broadcast system as active."""
        self.active = True
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None
        logger.info("[QFCWebSocketBroadcast] 🟢 Activated QFC WebSocket broadcast layer.")

    async def stop(self):
        """Gracefully stop the broadcast layer."""
        self.active = False
        logger.info("[QFCWebSocketBroadcast] 🔴 Broadcast layer stopped.")

    # -----------------------------------------
    #   Core Broadcast Methods
    # -----------------------------------------
    def send_state(self, session_id: str, field_tensor: Any, mode: str = "live") -> None:
        """
        Broadcasts a QFC field tensor update with session metadata.
        """
        if not self.active:
            logger.debug("[QFCWebSocketBroadcast] Broadcast skipped (inactive).")
            return

        payload = {
            "type": "qfc_state_update",
            "session_id": session_id,
            "field_tensor": field_tensor,
        }
        send_qfc_payload(payload, mode=mode)

    def send_payload(self, payload: Dict[str, Any], mode: str = "live") -> None:
        """Directly send an arbitrary payload."""
        if not self.active:
            logger.debug("[QFCWebSocketBroadcast] Broadcast skipped (inactive).")
            return
        send_qfc_payload(payload, mode)

    def send_beam_event(self, event: Union[Dict[str, Any], Any], event_type: str = "beam_update") -> None:
        """Send a beam-level symbolic event."""
        if not self.active:
            logger.debug("[QFCWebSocketBroadcast] Beam event skipped (inactive).")
            return
        broadcast_beam_event(event, event_type)


# ──────────────────────────────────────────────
#  CLI Test Harness
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import json
    import asyncio

    async def _test():
        qfc_ws = QFCWebSocketBroadcast()
        qfc_ws.start()
        qfc_ws.send_state("session_test", {"ψ": 0.87, "κ": 1.23, "τ": -0.04})
        qfc_ws.send_beam_event({"beam_id": "ψ_001", "coherence": 0.92}, "beam_update")
        await asyncio.sleep(0.5)
        await qfc_ws.stop()

    asyncio.run(_test())