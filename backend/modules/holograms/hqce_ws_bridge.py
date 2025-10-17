# ──────────────────────────────────────────────
#  Tessaris • HQCE WebSocket Bridge (Stage 12)
#  Real-time ψ–κ–T telemetry broadcast service
#  Used by GHX HUD + Codex runtime dashboards
# ──────────────────────────────────────────────

import json
import asyncio
import logging
import time
from typing import Dict, Any, Set

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

logger = logging.getLogger(__name__)


class HQCEWebSocketBridge:
    """
    Broadcast ψ–κ–T–C deltas to all connected clients.
    Designed for integration into HQCE Dashboard + GHX HUD.
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.last_broadcast: Dict[str, Any] = {}
        self.broadcast_interval = 0.5  # seconds between pushes

    # ────────────────────────────────────────────
    #  Connection Management
    # ────────────────────────────────────────────
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"[HQCEWebSocketBridge] 🟢 Client connected → {len(self.active_connections)} active")

    async def disconnect(self, websocket: WebSocket):
        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()
        self.active_connections.discard(websocket)
        logger.info(f"[HQCEWebSocketBridge] 🔴 Client disconnected → {len(self.active_connections)} active")

    # ────────────────────────────────────────────
    #  Broadcast
    # ────────────────────────────────────────────
    async def broadcast(self, tensor_data: Dict[str, Any]):
        """Send ψ–κ–T–C packet to all connected clients."""
        if not self.active_connections:
            return

        payload = {
            "type": "hqce_update",
            "timestamp": time.time(),
            "psi": tensor_data.get("psi"),
            "kappa": tensor_data.get("kappa"),
            "T": tensor_data.get("T"),
            "coherence": tensor_data.get("coherence"),
            "stability": tensor_data.get("stability", 0.0),
        }
        self.last_broadcast = payload
        msg = json.dumps(payload)

        for ws in list(self.active_connections):
            try:
                await ws.send_text(msg)
            except Exception as e:
                logger.warning(f"[HQCEWebSocketBridge] Failed to send to client: {e}")
                await self.disconnect(ws)

    # ────────────────────────────────────────────
    #  Periodic Loop
    # ────────────────────────────────────────────
    async def run_periodic_broadcast(self, get_tensor_state):
        """
        Continuously fetch ψκT state via callback and broadcast to clients.
        :param get_tensor_state: callable → returns Dict[ψ, κ, T, C]
        """
        logger.info("[HQCEWebSocketBridge] 🔁 Live broadcast loop started")
        while True:
            try:
                tensor = get_tensor_state()
                if tensor:
                    await self.broadcast(tensor)
                await asyncio.sleep(self.broadcast_interval)
            except asyncio.CancelledError:
                logger.info("[HQCEWebSocketBridge] ⏹ Broadcast loop stopped.")
                break
            except Exception as e:
                logger.error(f"[HQCEWebSocketBridge] Broadcast loop error: {e}")
                await asyncio.sleep(1.0)


# ──────────────────────────────────────────────
#  Singleton Bridge Instance
# ──────────────────────────────────────────────
hqce_ws_bridge = HQCEWebSocketBridge()