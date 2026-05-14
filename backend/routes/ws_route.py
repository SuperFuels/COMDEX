from fastapi import APIRouter, WebSocket
from backend.modules.websocket_manager import websocket_manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep the socket alive
    except Exception:
        await websocket_manager.disconnect(websocket)