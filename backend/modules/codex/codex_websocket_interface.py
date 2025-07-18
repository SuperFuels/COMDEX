# 📁 codex_websocket_interface.py
import asyncio
import websockets
import json
from backend.modules.codex.codex_core import CodexCore

connected_clients = set()
codex = CodexCore()

async def codex_handler(websocket, path):
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                glyph = data.get("glyph")
                context = data.get("context", {})
                if glyph:
                    result = codex.execute(glyph, context)
                    await websocket.send(json.dumps({"status": "ok", "result": result}))
            except Exception as e:
                await websocket.send(json.dumps({"status": "error", "error": str(e)}))
    finally:
        connected_clients.remove(websocket)


def start_codex_ws_server():
    return websockets.serve(codex_handler, "localhost", 8671)