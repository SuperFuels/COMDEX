# ✅ File: backend/modules/qwave/qwave_transfer_sender.py

from typing import Dict, Any
import asyncio

try:
    from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_update
except ImportError:
    broadcast_qfc_update = None
    print("⚠️ QFC bridge not found — QWave transfer disabled.")

def build_qwave_packet(source: str, beam_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": source,
        "payload": {
            "type": "qwave_transfer",
            "beam": beam_data,
        }
    }

def send_qwave_transfer(container_id: str, source: str, beam_data: Dict[str, Any]):
    if broadcast_qfc_update is None:
        return

    try:
        packet = build_qwave_packet(source, beam_data)
        asyncio.create_task(broadcast_qfc_update(container_id, packet))
        print(f"🚀 QWave transfer sent from {source} to {container_id}")
    except Exception as e:
        print(f"❌ QWave transfer failed: {e}")