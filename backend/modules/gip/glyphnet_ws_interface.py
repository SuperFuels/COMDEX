# File: backend/modules/glyphnet/glyphnet_ws_interface.py

import json
from typing import Dict, Any
from fastapi import WebSocket
from ..websocket_manager import register_client, unregister_client

connected_clients: Dict[int, WebSocket] = {}

async def glyphnet_ws_handler(websocket: WebSocket):
    await websocket.accept()
    client_id = id(websocket)
    connected_clients[client_id] = websocket

    try:
        register_client("glyphnet", websocket)
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if "subscribe" in msg:
                    websocket.extra_filters = msg["subscribe"]  # E.g. {symbol: "↔", target: "aion"}
                    await websocket.send_text(json.dumps({
                        "status": "subscribed",
                        "filters": websocket.extra_filters
                    }))
                else:
                    await broadcast_filtered(msg)
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "status": "error",
                    "message": str(e)
                }))
    except Exception:
        pass
    finally:
        unregister_client("glyphnet", websocket)
        connected_clients.pop(client_id, None)
        await websocket.close()

async def broadcast_filtered(packet: Dict[str, Any]):
    for ws in list(connected_clients.values()):
        filt = getattr(ws, "extra_filters", {})
        if match_filter(packet, filt):
            try:
                await ws.send_text(json.dumps(packet))
            except Exception:
                pass  # Fail silently on send errors

def match_filter(packet: Dict[str, Any], filt: Dict[str, Any]) -> bool:
    if not filt:
        return True
    glyphs = packet.get("glyphs", [])
    if "symbol" in filt:
        if not any(g.get("glyph") == filt["symbol"] for g in glyphs):
            return False
    if "target" in filt:
        if packet.get("meta", {}).get("container") != filt["target"]:
            return False
    if "priority" in filt:
        if packet.get("meta", {}).get("priority") != filt["priority"]:
            return False
    return True