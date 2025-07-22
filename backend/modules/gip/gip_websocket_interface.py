# backend/modules/gip/gip_websocket_interface.py

from fastapi import WebSocket
from .gip_executor import execute_gip_packet
from .gip_packet import GIPPacket
import json

async def handle_gip_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                packet_dict = json.loads(raw_data)
                gip_packet = GIPPacket(**packet_dict)
                
                response = execute_gip_packet(gip_packet)
                await websocket.send_text(json.dumps({
                    "status": "ok",
                    "response": response
                }))

            except Exception as e:
                await websocket.send_text(json.dumps({
                    "status": "error",
                    "message": str(e)
                }))
    except Exception:
        await websocket.close()