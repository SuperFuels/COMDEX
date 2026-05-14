# File: backend/modules/sci/sci_qfc_export_bridge.py

from typing import Any, Dict, Optional
from backend.modules.sci.sci_serializer import serialize_field_session, save_sci_container
import datetime
import os

class SCIQFCExportBridge:
    """
    D4: SCI QFC Export Bridge
    Enables on-demand export of the live QuantumFieldCanvas state to a .dc.json container.
    """

    def __init__(self):
        self.last_export_path: Optional[str] = None

    def export_current_field(
        self,
        field_state: Dict[str, Any],
        observer_id: Optional[str] = None,
        active_plugins: Optional[list[str]] = None,
        include_replay_log: bool = True,
        save_dir: str = "saved_sessions",
        name: Optional[str] = None
    ) -> str:
        """
        Serializes and saves the current QFC state as a .dc.json container.
        """
        try:
            container = serialize_field_session(
                field_state=field_state,
                observer_id=observer_id,
                active_plugins=active_plugins,
                include_replay_log=include_replay_log
            )
            export_path = save_sci_container(container, save_dir=save_dir, name=name)
            self.last_export_path = export_path
            print(f"📦 QFC export successful: {export_path}")
            return export_path
        except Exception as e:
            print(f"❌ QFC export failed: {e}")
            raise

    def get_last_export_path(self) -> Optional[str]:
        return self.last_export_path


# Optional test run
if __name__ == "__main__":
    dummy_field = {
        "nodes": [{"id": "a", "label": "init()"}],
        "links": [{"source": "a", "target": "b"}],
        "glyphs": [],
        "scrolls": [],
        "camera": {"position": [0, 1, 2]},
        "scroll_position": 2,
        "memory_trace_ids": ["trace_321"],
        "qwave_trace_hash": "hash789",
    }

    bridge = SCIQFCExportBridge()
    path = bridge.export_current_field(dummy_field, observer_id="observer007", active_plugins=["C2", "C5"])
    print(f"✅ Exported to: {path}")