# File: backend/modules/gip/gip_adapter_net.py

import json
from typing import Dict, Any
from fastapi import WebSocket
from .gip_packet import create_gip_packet, parse_gip_packet
from ..websocket_manager import broadcast_event

class GIPNetworkAdapter:
    def __init__(self, node_id: str):
        self.node_id = node_id

    def encode_packet(self, data: Dict[str, Any], destination: str) -> str:
        packet = create_gip_packet(sender=self.node_id, recipient=destination, payload=data)
        return json.dumps(packet)

    def decode_packet(self, raw_packet: str) -> Dict[str, Any]:
        try:
            return parse_gip_packet(json.loads(raw_packet))
        except Exception as e:
            return {"error": f"Invalid GIP packet: {str(e)}"}

    async def send_packet(self, websocket: WebSocket, data: Dict[str, Any], destination: str):
        packet = self.encode_packet(data, destination)
        await websocket.send_text(packet)

    async def broadcast_packet(self, data: Dict[str, Any], topic: str = "glyphnet"):
        packet = self.encode_packet(data, destination="broadcast")
        await broadcast_event(topic, json.loads(packet))