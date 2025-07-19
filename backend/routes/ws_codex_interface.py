from fastapi import APIRouter, WebSocket
from backend.modules.codex.codex_websocket_interface import codex_ws_handler

router = APIRouter()

@router.websocket("/ws/codex")
async def codex_ws(websocket: WebSocket):
    await codex_ws_handler(websocket)