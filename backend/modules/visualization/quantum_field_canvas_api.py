# ✅ File: backend/modules/visualization/quantum_field_canvas_api.py

import json
from typing import Dict, Any
from backend.modules.visualization.qfc_websocket_bridge import send_qfc_update

def trigger_qfc_render(payload: Dict[str, Any]) -> None:
    """
    Trigger a Quantum Field Canvas (QFC) render update based on a symbolic glyph payload.
    This function sends a broadcast or WebSocket update to the QFC viewer.

    Args:
        payload (Dict[str, Any]): Glyph or symbolic data to visualize.
    """
    try:
        render_packet = {
            "type": "qfc_render_trigger",
            "source": "creative_synthesis",
            "payload": payload
        }

        # WebSocket or symbolic broadcast to frontend (GHX/HUD)
        send_qfc_update(render_packet)

        print("🎨 QFC render triggered successfully.")

    except Exception as e:
        print(f"⚠️ Failed to trigger QFC render: {e}")