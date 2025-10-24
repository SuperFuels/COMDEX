# ================================================================
# ⚡ Phase 45G.15 — GHX CodexMetrics WebSocket Push Bridge
# ================================================================
"""
Broadcasts CodexMetrics overlay updates over WebSocket for GHX UI dashboards.

Inputs:
    data/telemetry/codexmetrics_overlay.json
Outputs:
    WebSocket stream (ws://localhost:8765/ghx)
    Live dashboard data packets:
        {
            "habit_strength": ...,
            "delta": ...,
            "avg_ρ": ...,
            "avg_I": ...,
            "avg_grad": ...
        }
"""

import asyncio, json, time, logging
from pathlib import Path
import websockets

logger = logging.getLogger(__name__)
OVERLAY_PATH = Path("data/telemetry/codexmetrics_overlay.json")

class CodexMetricsWSPush:
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.last_sent_timestamp = 0.0

    async def handler(self, websocket):
        logger.info(f"[CodexWS] Client connected: {websocket.remote_address}")
        try:
            while True:
                await self.check_and_send(websocket)
                await asyncio.sleep(2)  # poll interval
        except websockets.ConnectionClosed:
            logger.info("[CodexWS] Client disconnected.")

    async def check_and_send(self, websocket):
        """Read overlay file and push update if timestamp changed."""
        if not OVERLAY_PATH.exists():
            return
        try:
            data = json.load(open(OVERLAY_PATH))
            ts = data.get("timestamp", 0)
            if ts > self.last_sent_timestamp:
                await websocket.send(json.dumps(data))
                self.last_sent_timestamp = ts
                logger.info(f"[CodexWS] Broadcasted update → {data}")
        except Exception as e:
            logger.error(f"[CodexWS] Failed to broadcast: {e}")

    async def start_server(self):
        logger.info(f"[CodexWS] Starting WebSocket server on ws://{self.host}:{self.port}/ghx")
        async with websockets.serve(self.handler, self.host, self.port, ping_interval=None):
            await asyncio.Future()  # run forever


# ------------------------------------------------------------
# CLI Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    server = CodexMetricsWSPush()
    asyncio.run(server.start_server())