# File: backend/modules/gip/gip_adapter_net.py

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket

from .gip_packet import create_gip_packet, parse_gip_packet
from ..websocket_manager import broadcast_event  # async: broadcast_event(tag, payload)

logger = logging.getLogger(__name__)


def _fire_and_forget(coro) -> None:
    """Schedule a coroutine from sync code without blocking the caller."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        # No running loop in this thread; best-effort run.
        try:
            asyncio.run(coro)
        except Exception:
            pass


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

    async def send_packet(self, websocket: WebSocket, data: Dict[str, Any], destination: str) -> None:
        packet = self.encode_packet(data, destination)
        await websocket.send_text(packet)

    async def broadcast_packet(self, data: Dict[str, Any], topic: str = "glyphnet") -> None:
        """
        Broadcast a GIP packet over the shared websocket manager bus.

        NOTE:
          websocket_manager.broadcast_event(tag, payload) expects:
            - tag: str
            - payload: Dict[str, Any]
        """
        raw = self.encode_packet(data, destination="broadcast")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"type": "gip_packet", "raw": raw, "sender": self.node_id}

        await broadcast_event(topic, payload)


# ══════════════════════════════════════════════════════
# 🔁 Legacy GIP Adapter Hooks for GlyphWave Compatibility
# These can be used by GlyphWave if gw_enabled() is False
# ══════════════════════════════════════════════════════

def legacy_send_gip_packet(packet: Dict[str, Any]) -> None:
    """
    Legacy fallback to broadcast a GIP packet via classic broadcast path.
    Sync shim: schedules the async broadcast_event() safely.
    """
    try:
        sender = packet.get("sender_id") or packet.get("sender") or "unknown"
        recipient = packet.get("recipient_id") or packet.get("recipient") or "broadcast"
        payload_in = packet.get("payload", {})

        adapter = GIPNetworkAdapter(node_id=str(sender))
        raw = adapter.encode_packet(payload_in if isinstance(payload_in, dict) else {"payload": payload_in}, destination=str(recipient))

        try:
            decoded = json.loads(raw)
        except Exception:
            decoded = {"type": "gip_packet", "raw": raw, "sender": sender, "recipient": recipient}

        _fire_and_forget(broadcast_event("glyphnet", decoded))

    except Exception as e:
        logger.warning(f"[GIP Fallback] Failed to send packet: {e}")


def legacy_recv_gip_packet() -> Optional[Dict[str, Any]]:
    """
    Placeholder for receiving GIP packets from legacy channels.
    To be polled if GlyphWave is disabled.
    """
    return None