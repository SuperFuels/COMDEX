# ✅ File: backend/modules/visualization/trigger_qfc_render.py

from typing import Optional
from backend.modules.visualization.beam_payload_builder import build_test_beam_payload
from backend.modules.visualization.qfc_websocket_bridge import send_qfc_update

# 🚀 Trigger QFC Render Update
def trigger_qfc_render(container_id: Optional[str] = None, tick: Optional[int] = None) -> None:
    """
    Builds a QFC render payload and broadcasts it to all QFC WebSocket clients.

    Args:
        container_id (str, optional): Optional container ID for filtering logic (future use).
        tick (int, optional): Optional tick to render a specific frame (future use).
    """
    try:
        # 🔧 For now, just use the test payload builder
        payload = build_test_beam_payload()

        # 🌐 Send to WebSocket clients
        send_qfc_update(payload)
        print("✅ QFC render triggered successfully.")

    except Exception as e:
        print(f"❌ Failed to trigger QFC render: {e}")