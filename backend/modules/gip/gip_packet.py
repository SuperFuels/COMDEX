# File: backend/modules/gip/gip_packet.py

from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import time
import uuid

@dataclass
class GIPPacket:
    id: str
    timestamp: float
    sender: str
    recipient: str
    payload: Dict[str, Any]
    type: str = "gip"
    encoding: str = "glyph"
    compression: str = "symbolic"

    @classmethod
    def create(cls, sender: str, recipient: str, payload: Dict[str, Any]) -> "GIPPacket":
        return cls(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            sender=sender,
            recipient=recipient,
            payload=payload
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GIPPacket":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", time.time()),
            sender=data["sender"],
            recipient=data["recipient"],
            payload=data["payload"],
            type=data.get("type", "gip"),
            encoding=data.get("encoding", "glyph"),
            compression=data.get("compression", "symbolic"),
        )

# Legacy compatibility

def create_gip_packet(sender: str, recipient: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return GIPPacket.create(sender, recipient, payload).to_dict()

def parse_gip_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    gip = GIPPacket.from_dict(packet)
    return gip.to_dict()