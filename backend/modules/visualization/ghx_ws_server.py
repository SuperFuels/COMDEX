# ===============================
# 📁 backend/modules/visualization/ghx_ws_server.py
# ===============================
"""
🌐 GHX WebSocket Server — Live Coherence Stream
------------------------------------------------
Bridges Tessaris GHXFeedbackBridge telemetry packets into a real-time
WebSocket broadcast endpoint for CodexHUD, GHXVisualizer, or custom dashboards.

Usage:
    PYTHONPATH=. python backend/modules/visualization/ghx_ws_server.py
Then connect a WebSocket client to ws://localhost:8765
"""

import asyncio
import json
import websockets
from typing import List

# Global connection set
connected_clients: List[websockets.WebSocketServerProtocol] = []


async def handler(websocket):
    """Register new connections and stream packets."""
    connected_clients.append(websocket)
    print(f"🛰️  New GHX client connected ({len(connected_clients)} active)")
    try:
        async for message in websocket:
            # Echo-back or route commands if needed
            print(f"[GHX_WS] Received command: {message}")
    except Exception as e:
        print(f"[GHX_WS] Client error: {e}")
    finally:
        connected_clients.remove(websocket)
        print("🛰️  GHX client disconnected.")


async def broadcast(packet: dict):
    """Broadcast GHX packet to all connected clients."""
    if not connected_clients:
        return
    data = json.dumps(packet)
    await asyncio.gather(*(ws.send(data) for ws in connected_clients if ws.open))


async def start_server():
    """Launch GHX WebSocket broadcast server."""
    server = await websockets.serve(handler, "localhost", 8765)
    print("🌈 GHX WebSocket server active @ ws://localhost:8765")
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(start_server())