# File: backend/modules/teleport/teleport_packet.py

from typing import Dict, Any
from datetime import datetime
import uuid
import asyncio

from backend.modules.teleport.portal_manager import PORTALS
from backend.modules.websocket_manager import websocket_manager

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


# ✅ Symbolic GlyphPush Sender (Replay Logic)
async def send_glyphpush_packet(data: Dict[str, Any]) -> bool:
    """
    Broadcasts a symbolic replay packet triggered by a glyph (↔, ⮁).
    Auto-creates a portal if needed. Dispatches via WebSocket and portal.
    """
    try:
        from backend.modules.runtime.container_runtime import ContainerRuntime
        container_id = data.get("from")
        target_id = data.get("to") or container_id
        now = datetime.utcnow().timestamp()

        payload = {
            "replay_trace": data.get("trace", []),
            "trigger": data.get("trigger"),
            "meta": {
                "seed": data.get("glyph"),
                "origin": container_id,
                "mode": "replay",
                "phase_info": {
                    "emitted_by": "teleport_packet",
                    "timestamp_seed": now,
                    "warp_context": "edge"
                }
            }
        }

        # Reuse or register symbolic portal
        portal_id = data.get("portal_id") or PORTALS.register_portal(container_id, target_id)
        packet = TeleportPacket(
            source=container_id,
            destination=target_id,
            payload=payload,
            container_id=container_id,
            portal_id=portal_id
        )

        # Broadcast to WebSocket
        await websocket_manager.broadcast({
            "event": "glyph_push",
            "payload": packet.to_dict()
        })

        # Trigger portal delivery immediately
        runtime = ContainerRuntime()
        runtime.load_glyphpush_packet(packet)

        return True
    except Exception as e:
        print(f"[⚠️] Failed to send GlyphPush packet: {e}")
        return False