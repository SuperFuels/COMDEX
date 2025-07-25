# backend/routes/ws/glyph_socket_ws.py

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from backend.modules.glyphnet.glyph_socket import GlyphSocket
import json

router = APIRouter()
glyph_socket = GlyphSocket()

@router.websocket("/ws/glyph_socket")
async def websocket_glyph_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            result = glyph_socket.dispatch(payload)
            await websocket.send_json(result)
    except WebSocketDisconnect:
        await websocket.close()