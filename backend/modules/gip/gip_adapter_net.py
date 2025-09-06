# File: backend/modules/gip/gip_adapter_net.py

import json
from typing import Dict, Any, Optional
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


# ══════════════════════════════════════════════════════
# 🔁 Legacy GIP Adapter Hooks for GlyphWave Compatibility
# These can be used by GlyphWave if gw_enabled() is False
# ══════════════════════════════════════════════════════

def legacy_send_gip_packet(packet: Dict[str, Any]) -> None:
    """
    Legacy fallback to broadcast GIP packet via classic broadcast path.
    Used by GlyphWave when disabled.
    """
    try:
        adapter = GIPNetworkAdapter(node_id=packet.get("sender_id", "unknown"))
        raw = adapter.encode_packet(packet.get("payload", {}), destination=packet.get("recipient_id", "broadcast"))
        # Synchronously broadcast using FastAPI bus
        # You may replace this with your actual legacy emitter if not broadcast_event
        broadcast_event("glyphnet", json.loads(raw))
    except Exception as e:
        print(f"[GIP Fallback] Failed to send packet: {e}")


def legacy_recv_gip_packet() -> Optional[Dict[str, Any]]:
    """
    Placeholder for receiving GIP packets from legacy channels.
    To be polled if GlyphWave is disabled.
    """
    # NOTE: You must replace this with your actual receive queue/socket
    # If unavailable, return None to gracefully skip
    return None  # or: return next_packet_from_queue()