# ================================================================
# ⚡ Phase 45G.15 - GHX CodexMetrics WebSocket Push Bridge (lazy + pytest-safe)
# ================================================================
"""
Broadcasts CodexMetrics overlay updates over WebSocket for GHX UI dashboards.

Inputs:
    data/telemetry/codexmetrics_overlay.json
Outputs:
    WebSocket stream (ws://localhost:8765/ghx)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)
OVERLAY_PATH = Path("data/telemetry/codexmetrics_overlay.json")

# Optional dependency (avoid hard-fail on import in CI/tests)
try:
    import websockets  # type: ignore
except Exception:  # pragma: no cover
    websockets = None  # type: ignore


def _quiet_enabled() -> bool:
    return os.getenv("TESSARIS_TEST_QUIET") == "1"


class CodexMetricsWSPush:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        overlay_path: Path = OVERLAY_PATH,
        poll_s: float = 2.0,
    ):
        self.host = str(host)
        self.port = int(port)
        self.overlay_path = Path(overlay_path)
        self.poll_s = float(poll_s)
        self.last_sent_timestamp = 0.0

    async def handler(self, websocket: Any):
        ra = getattr(websocket, "remote_address", None)
        logger.info(f"[CodexWS] Client connected: {ra}")
        try:
            while True:
                await self.check_and_send(websocket)
                await asyncio.sleep(self.poll_s)
        except Exception:
            # websockets.ConnectionClosed isn’t always available if websockets import is stubbed
            logger.info("[CodexWS] Client disconnected.")

    async def check_and_send(self, websocket: Any) -> None:
        """Read overlay file and push update if timestamp changed."""
        if not self.overlay_path.exists():
            return
        try:
            with self.overlay_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            ts = float(data.get("timestamp", 0) or 0)
            if ts > self.last_sent_timestamp:
                await websocket.send(json.dumps(data, ensure_ascii=False))
                self.last_sent_timestamp = ts
                logger.info("[CodexWS] Broadcasted update")
        except Exception as e:
            logger.error(f"[CodexWS] Failed to broadcast: {e}")

    async def start_server(self) -> None:
        if websockets is None:  # pragma: no cover
            raise RuntimeError("websockets dependency not available; install websockets to run CodexMetricsWSPush")

        logger.info(f"[CodexWS] Starting WebSocket server on ws://{self.host}:{self.port}/ghx")
        async with websockets.serve(self.handler, self.host, self.port, ping_interval=None):  # type: ignore[attr-defined]
            await asyncio.Future()  # run forever


# ─────────────────────────────────────────────
# Lazy singleton (NO import-time runtime bring-up)
# ─────────────────────────────────────────────
_SERVER: Optional[CodexMetricsWSPush] = None


def get_server() -> CodexMetricsWSPush:
    global _SERVER
    if _SERVER is None:
        _SERVER = CodexMetricsWSPush()
        if not _quiet_enabled():
            logger.info("[CodexWS] CodexMetricsWSPush initialized (lazy)")
    return _SERVER


class _ServerProxy:
    def __getattr__(self, name: str):
        return getattr(get_server(), name)


# Back-compat import without eager init.
SERVER = _ServerProxy()


# ------------------------------------------------------------
# CLI Entry
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(get_server().start_server())