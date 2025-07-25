# backend/modules/teleport/teleport_packet.py

from typing import Dict, Any
from datetime import datetime
import uuid

class TeleportPacket:
    """
    A symbolic teleport packet that moves glyph or container logic
    from one node to another, compatible with SEC/HSC runtime.
    """

    def __init__(self, source: str, destination: str, payload: Dict[str, Any], container_id: str, portal_id: str):
        self.packet_id = str(uuid.uuid4())
        self.source = source
        self.destination = destination
        self.container_id = container_id
        self.portal_id = portal_id
        self.timestamp = datetime.utcnow().isoformat()
        self.payload = payload

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "source": self.source,
            "destination": self.destination,
            "container_id": self.container_id,
            "portal_id": self.portal_id,
            "timestamp": self.timestamp,
            "payload": self.payload
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TeleportPacket":
        pkt = TeleportPacket(
            source=data["source"],
            destination=data["destination"],
            payload=data["payload"],
            container_id=data["container_id"],
            portal_id=data["portal_id"]
        )
        pkt.packet_id = data["packet_id"]
        pkt.timestamp = data["timestamp"]
        return pkt
        backend/modules/teleport/teleport_packet.py
        backend/modules/teleport/portal_manager.py