# File: backend/routes/ws/qglyph_ws.py

from fastapi import WebSocket
from backend.modules.sqi.qglyph_ws_interface import qglyph_ws_handler

# ✅ FastAPI WebSocket route mount for QGlyph execution
async def start_qglyph_ws(websocket: WebSocket):
    await qglyph_ws_handler(websocket)