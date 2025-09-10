# backend/modules/visualization/qfc_renderer_trigger.py

from typing import Dict, Any
from backend.modules.visualization.qfc_websocket_bridge import send_qfc_update
from backend.modules.visualization.beam_payload_builder import build_test_mixed_beam_data  # or live builder

def trigger_qfc_render(container_id: str = "test_pattern_container") -> Dict[str, Any]:
    """
    Trigger a symbolic QFC render and broadcast to all connected WebSocket clients.
    
    Args:
        container_id (str): Optional container to render from. Defaults to test pattern container.
    
    Returns:
        Dict[str, Any]: Render payload sent to clients.
    """
    try:
        # 🔄 Swap this for live QFC data when ready
        render_payload = build_test_mixed_beam_data()
        send_qfc_update(render_payload)
        return {"status": "success", "container": container_id, "rendered": render_payload}
    except Exception as e:
        return {"status": "failed", "error": str(e)}