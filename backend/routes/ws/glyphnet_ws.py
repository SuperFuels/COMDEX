# File: backend/routes/ws/glyphnet_ws.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from modules.gip.gip_adapter_net import GIPNetworkAdapter
from modules.gip.gip_executor import handle_gip_packet

router = APIRouter()
adapter = GIPNetworkAdapter(node_id="glyphnet-node")

@router.websocket("/ws/glyphnet")
async def glyphnet_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw_data = await websocket.receive_text()
            packet = adapter.decode_packet(raw_data)
            response = handle_gip_packet(packet)
            await adapter.send_packet(websocket, response, destination=packet.get("sender", "unknown"))
    except WebSocketDisconnect:
        pass