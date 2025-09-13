# ✅ File: backend/modules/visualization/quantum_field_canvas_api.py

import json
from typing import Dict, Any
from backend.modules.visualization.qfc_websocket_bridge import send_qfc_update

async def trigger_qfc_render(payload: Dict[str, Any], source: str = "creative_synthesis") -> None:
    """
    Trigger a Quantum Field Canvas (QFC) render update based on a symbolic glyph payload.
    This function sends a structured WebSocket update to the QFC viewer.

    Args:
        payload (Dict[str, Any]): Glyph or symbolic data to visualize.
        source (str): Source tag for the render event (e.g., 'creative_synthesis', 'mutation_loop')
    """
    try:
            render_packet = {
                "type": "qfc_render_trigger",
                "source": source,
                "payload": payload
            }

            await send_qfc_update(render_packet)  # ✅ Properly awaited
            print(f"🎨 QFC render triggered successfully from [{source}]")

        except Exception as e:
            print(f"⚠️ Failed to trigger QFC render from [{source}]: {e}")