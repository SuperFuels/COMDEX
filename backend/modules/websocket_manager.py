from __future__ import annotations

from fastapi import WebSocket
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from collections import defaultdict
import asyncio
import json
import os
import time

if TYPE_CHECKING:
    from backend.modules.symbolic_engine.math_logic_kernel import LogicGlyph


# ------------------------------------------------------------
# Perf/verbosity tuning
# ------------------------------------------------------------
# Default: do NOT spam logs in hot paths.
WS_QUIET = os.getenv("AION_WS_QUIET", "1").lower() in {"1", "true", "yes", "on"}

# If you REALLY want the "Broadcasting to 0 clients" line, enable it explicitly:
WS_LOG_NOCLIENT = os.getenv("AION_WS_LOG_NOCLIENT", "0").lower() in {"1", "true", "yes", "on"}

# If enabled, rate-limit that log line (seconds)
WS_NOCLIENT_LOG_MIN_INTERVAL_S = float(os.getenv("AION_WS_NOCLIENT_LOG_MIN_INTERVAL_S", "10"))


class WebSocketClient:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.tags: set[str] = set()
        self.extra_filters: Dict[str, Any] = {}


class WebSocketManager:
    def __init__(self):
        self.clients: List[WebSocketClient] = []
        self.tag_map: Dict[str, List[WebSocketClient]] = defaultdict(list)

        # rate-limit for "0 clients" log
        self._last_no_client_log_ts: float = 0.0

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        client = WebSocketClient(websocket)
        self.clients.append(client)
        if not WS_QUIET:
            print(f"[🔌] WebSocket connected: {len(self.clients)} clients")

    def disconnect(self, websocket: WebSocket):
        client = next((c for c in self.clients if c.websocket == websocket), None)
        if not client:
            return

        try:
            self.clients.remove(client)
        except ValueError:
            pass

        # Remove from tag buckets (best-effort)
        for tag in list(client.tags):
            bucket = self.tag_map.get(tag)
            if bucket and client in bucket:
                try:
                    bucket.remove(client)
                except ValueError:
                    pass

        if not WS_QUIET:
            print(f"[⚡] WebSocket disconnected: {len(self.clients)} clients")

    async def subscribe(self, websocket: WebSocket, tag: str, filters: Optional[Dict[str, Any]] = None):
        client = next((c for c in self.clients if c.websocket == websocket), None)
        if not client:
            return

        # de-dupe subscription
        if tag not in client.tags:
            client.tags.add(tag)
            bucket = self.tag_map[tag]
            if client not in bucket:
                bucket.append(client)

        if filters:
            client.extra_filters = filters

        if not WS_QUIET:
            print(f"[📡] Subscribed client to tag: {tag} with filters: {filters or '{}'}")

    async def unsubscribe(self, websocket: WebSocket, tag: str):
        client = next((c for c in self.clients if c.websocket == websocket), None)
        if not client or tag not in client.tags:
            return

        client.tags.remove(tag)
        bucket = self.tag_map.get(tag)
        if bucket and client in bucket:
            try:
                bucket.remove(client)
            except ValueError:
                pass

        if not WS_QUIET:
            print(f"[❌] Unsubscribed client from tag: {tag}")

    async def broadcast(self, message: Dict[str, Any], tag: Optional[str] = None, origin_id: Optional[str] = None):
        """
        Send a message to all clients or to a subset based on tag and filter.

        PERF PRINCIPLES:
          - No asyncio.gather / wait_for / semaphores by default (hot path safe).
          - Do not create empty tag buckets (use .get for tag lookup).
          - Minimal work when there are no clients.
        """
        target_clients = (self.tag_map.get(tag, []) if tag else self.clients)

        # Fast path: no clients
        if not target_clients:
            if WS_LOG_NOCLIENT and not WS_QUIET:
                now = time.time()
                if (now - self._last_no_client_log_ts) >= WS_NOCLIENT_LOG_MIN_INTERVAL_S:
                    self._last_no_client_log_ts = now
                    print(f"[📣] Broadcasting to 0 clients {'on tag: ' + tag if tag else '(global)'}")
            return

        enriched_msg = message.copy()
        if origin_id:
            enriched_msg["origin"] = origin_id

        text = json.dumps(enriched_msg)

        # Sequential send is fastest for small N and avoids task overhead.
        # If a socket dies, drop it.
        dead: List[WebSocketClient] = []

        for client in list(target_clients):
            try:
                filters = client.extra_filters
                if filters:
                    if "symbol" in filters and filters["symbol"] != message.get("symbol"):
                        continue
                    if "target" in filters and filters["target"] != message.get("meta", {}).get("container"):
                        continue

                await client.websocket.send_text(text)

            except Exception:
                dead.append(client)

        # cleanup dead sockets
        for client in dead:
            try:
                self.disconnect(client.websocket)
            except Exception:
                pass


# ✅ Singleton instance for global use
websocket_manager = WebSocketManager()

# 🔁 Back-compat alias expected by some modules
manager = websocket_manager

# ✅ Global helper for GIP or other modules
async def broadcast_event(tag: str, payload: Dict[str, Any]):
    await websocket_manager.broadcast(payload, tag=tag)

# ✅ New symbolic glyph broadcaster
async def broadcast_symbolic_glyph(glyph: "LogicGlyph"):
    payload = {
        "type": "symbolic_glyph",
        "glyph": glyph.to_dict() if hasattr(glyph, "to_dict") else str(glyph),
    }
    await broadcast_event("symbolic_glyph", payload)

# ✅ Legacy alias for compatibility
async def send_ws_message(payload: Dict[str, Any], tag: Optional[str] = None):
    await websocket_manager.broadcast(payload, tag=tag)

__all__ = [
    "WebSocketManager",
    "websocket_manager",
    "manager",
    "broadcast_event",
    "broadcast_symbolic_glyph",
    "send_ws_message",
]