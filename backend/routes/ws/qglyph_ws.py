# File: backend/routes/ws/qglyph_ws.py

from fastapi import APIRouter, WebSocket
from typing import Any
from backend.modules.glyphos.qglyph_ws_interface import qglyph_ws_handler

# Create a router so main.py can include it normally
router = APIRouter()

@router.websocket("/ws/qglyph")
async def qglyph_socket(websocket: WebSocket) -> Any:
    """
    Canonical WebSocket endpoint for QGlyph.
    Delegates all handling to qglyph_ws_handler.
    """
    await qglyph_ws_handler(websocket)

# ---- Back-compat shims (keep old usage working) -----------------------------

async def start_qglyph_ws(websocket: WebSocket) -> Any:
    """
    OLD signature some code paths used: start_qglyph_ws(websocket).
    Forward directly to the handler to avoid breaking callers.
    """
    await qglyph_ws_handler(websocket)

def start_qglyph_ws_app(app) -> bool:
    """
    If some older main.py calls start_qglyph_ws(app), include the router.
    """
    app.include_router(router)
    return True

__all__ = ["router", "start_qglyph_ws", "start_qglyph_ws_app"]