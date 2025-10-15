# ──────────────────────────────────────────────
#  Tessaris • HST WebSocket Streamer (Unified)
#  Combines symbolic overlay + P5 replay streaming
#  for GHX/QFC + Holographic Core integration
# ──────────────────────────────────────────────

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Any

from backend.modules.symbolic.symbolic_meaning_tree import SymbolicMeaningTree
from backend.modules.websocket_manager import broadcast_event

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Legacy + Symbolic Overlay Support
# ──────────────────────────────────────────────
def stream_hst_to_websocket(container_id: str, tree: SymbolicMeaningTree, context: Optional[str] = None):
    """
    Broadcast the SymbolicMeaningTree nodes/edges to GHX/QFC overlay clients via WebSocket.
    """
    try:
        payload = {
            "type": "hst_overlay",
            "container_id": container_id,
            "nodes": [n.to_dict() for n in tree.node_index.values()],
            "edges": [
                {"from": edge.source, "to": edge.target, "type": edge.type}
                for edge in tree.edges
            ],
            "context": context or "runtime"
        }
        asyncio.create_task(broadcast_event("hst_overlay", payload))
        print(f"📡 HST overlay broadcasted for {container_id} with {len(tree.node_index)} nodes")
    except Exception as e:
        print(f"❌ Failed to stream HST overlay: {e}")


def broadcast_replay_paths(container_id: str, replay_paths: List[Dict], context: Optional[str] = None):
    """
    Broadcast replay path overlays (mutation or prediction trails) to GHX/QFC visualizers.
    """
    try:
        payload = {
            "type": "replay_trails",
            "container_id": container_id,
            "replay_paths": replay_paths,
            "context": context or "prediction_engine"
        }
        asyncio.create_task(broadcast_event("replay_trails", payload))
        print(f"🛰️ Replay trails broadcasted for {container_id} ({len(replay_paths)} paths)")
    except Exception as e:
        print(f"❌ Failed to broadcast replay trails: {e}")

# ──────────────────────────────────────────────
#  HQCE P5 Extension: HST Field & Replay Streamer
# ──────────────────────────────────────────────

import websockets


class HSTWebSocketStreamer:
    """
    Real-time WebSocket broadcaster for HST field nodes,
    ψ–κ–T tensors, LightWave beams, and replay visualization.
    """

    def __init__(self, uri: str = "ws://localhost:8765/hst", buffer_limit: int = 256):
        self.uri = uri
        self.clients: List[websockets.WebSocketServerProtocol] = []
        self.replay_buffer: List[Dict[str, Any]] = []
        self.buffer_limit = buffer_limit
        self.last_broadcast_time = 0.0
        self.broadcast_interval = 0.5  # seconds between updates

    # ────────────────────────────────────────────
    #  Client Lifecycle
    # ────────────────────────────────────────────
    async def register(self, websocket):
        self.clients.append(websocket)
        logger.info(f"[HSTStreamer] Client connected ({len(self.clients)})")

    async def unregister(self, websocket):
        if websocket in self.clients:
            self.clients.remove(websocket)
            logger.info(f"[HSTStreamer] Client disconnected ({len(self.clients)})")

    # ────────────────────────────────────────────
    #  Core Broadcast Logic
    # ────────────────────────────────────────────
    async def broadcast(self, data: Dict[str, Any]):
        """
        Broadcast payload to all connected HST clients.
        """
        if not self.clients:
            logger.debug("[HSTStreamer] No clients connected; skipping broadcast.")
            return

        msg = json.dumps(data, ensure_ascii=False)
        for ws in self.clients.copy():
            try:
                await ws.send(msg)
            except Exception as e:
                logger.warning(f"[HSTStreamer] Dropping client due to error: {e}")
                await self.unregister(ws)

    def append_replay_frame(self, frame: Dict[str, Any]):
        """
        Append new HST replay frame to rolling buffer.
        """
        self.replay_buffer.append(frame)
        if len(self.replay_buffer) > self.buffer_limit:
            self.replay_buffer.pop(0)

    async def broadcast_replay_paths(self, payload: Dict[str, Any]):
        """
        Main replay broadcast entry (P5 E3 link).
        """
        now = time.time()
        if (now - self.last_broadcast_time) < self.broadcast_interval:
            return

        self.last_broadcast_time = now
        payload["type"] = "hst_replay_update"
        payload["frame_count"] = len(payload.get("nodes", []))
        payload["timestamp"] = time.time()
        self.append_replay_frame(payload)

        await self.broadcast(payload)
        logger.debug(f"[HSTStreamer] Sent replay frame ({payload['frame_count']} nodes)")

    # ────────────────────────────────────────────
    #  WebSocket Server Loop
    # ────────────────────────────────────────────
    async def handler(self, websocket, path):
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get("cmd") == "replay_request":
                        await self._handle_replay_request(websocket, data)
                    elif data.get("cmd") == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                except Exception as e:
                    logger.warning(f"[HSTStreamer] Client message error: {e}")
        finally:
            await self.unregister(websocket)

    async def _handle_replay_request(self, websocket, data: Dict[str, Any]):
        """
        Handle client replay history requests.
        """
        logger.info(f"[HSTStreamer] Replay request → {len(self.replay_buffer)} frames available")
        for frame in self.replay_buffer[-50:]:
            await websocket.send(json.dumps(frame))
            await asyncio.sleep(0.05)

    def run_server(self, host: str = "0.0.0.0", port: int = 8765):
        """
        Launch async WebSocket server for holographic replay streaming.
        """
        async def start_server():
            async with websockets.serve(self.handler, host, port):
                logger.info(f"[HSTStreamer] Serving on ws://{host}:{port}/hst")
                await asyncio.Future()  # run forever

        try:
            asyncio.run(start_server())
        except KeyboardInterrupt:
            logger.info("[HSTStreamer] Shutting down.")
        except Exception as e:
            logger.error(f"[HSTStreamer] Server error: {e}")

# ──────────────────────────────────────────────
#  Global Singleton + Compatibility Wrapper
# ──────────────────────────────────────────────

_streamer: Optional[HSTWebSocketStreamer] = None

def get_streamer() -> HSTWebSocketStreamer:
    global _streamer
    if _streamer is None:
        _streamer = HSTWebSocketStreamer()
    return _streamer

def broadcast_replay_paths_hst(payload: Dict[str, Any]):
    """
    Compatibility function for HSTVisualizationBridge.
    Spawns async broadcast coroutine automatically.
    """
    streamer = get_streamer()
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    try:
        asyncio.get_event_loop().create_task(streamer.broadcast_replay_paths(payload))
    except Exception:
        asyncio.run(streamer.broadcast_replay_paths(payload))