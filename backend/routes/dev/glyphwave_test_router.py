from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Any, Dict, Optional

from backend.modules.glyphwave.adapters import get_runtime, send_packet, recv_packet

router = APIRouter()

class TestWavePacket(BaseModel):
    sender_id: str
    recipient_id: str
    payload: Dict[str, Any]
    channel: Optional[str] = "test"
    gain: Optional[float] = 0.5
    duration: Optional[float] = 1.0

@router.get("/gw/state")
def get_glyphwave_state():
    """
    📡 Returns internal GlyphWave runtime state (debug only)
    """
    runtime = get_runtime()
    return {
        "gw_enabled": runtime.enabled,
        "queued_packets": len(runtime._recv_queue),
        "sent_packets": len(runtime._sent_packets),
        "modulation_log": runtime._modulation_log[-10:]  # recent only
    }

@router.post("/gw/send")
def send_test_wave(packet: TestWavePacket):
    """
    📬 Send a test GIP/GWIP wave packet into GlyphWave system
    """
    send_packet(packet.dict())
    return {"status": "sent", "packet": packet}

@router.get("/gw/recv")
def receive_test_wave():
    """
    📥 Receive one test packet (if available)
    """
    packet = recv_packet()
    if packet:
        return {"status": "received", "packet": packet}
    return {"status": "empty", "packet": None}