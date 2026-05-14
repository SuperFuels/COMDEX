from fastapi import APIRouter, WebSocket
from backend.modules.holograms.ghx_ws_interface import ghx_ws_handler

router = APIRouter()

@router.websocket("/ws/ghx/{container_id}")
async def websocket_endpoint(websocket: WebSocket, container_id: str):
    await ghx_ws_handler.connect(websocket, container_id)
    try:
        while True:
            data = await websocket.receive_text()
            await ghx_ws_handler.receive(websocket, data)
    except Exception:
        await ghx_ws_handler.disconnect(websocket)