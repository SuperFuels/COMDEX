from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from backend.modules.gip.gip_websocket_interface import handle_gip_packet

router = APIRouter()

active_connections = set()

@router.websocket("/ws/gip")
async def websocket_gip_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                response = await handle_gip_packet(data)
                await websocket.send_text(response)
            except Exception as e:
                await websocket.send_text(f"Error processing GIP packet: {str(e)}")
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        active_connections.remove(websocket)
        print(f"WebSocket error: {e}")
