# File: backend/modules/sci/sci_core.py

import os
import json
from typing import Dict, List, Optional, Any

from backend.modules.sci.scroll_engine import ScrollEngine
from backend.modules.qfc.qfc_runtime import QuantumFieldCanvas
from backend.modules.sci.engine_dock import EngineDock
from backend.modules.sci.field_tab_manager import FieldTabManager
from backend.modules.sci.sci_file_manager import SCIFileManager


class SpatialCognitionInterface:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.scroll_engine = ScrollEngine(user_id)
        self.qfc = QuantumFieldCanvas()
        self.engine_dock = EngineDock()
        self.tab_manager = FieldTabManager()
        self.file_manager = SCIFileManager(user_id)
        self.active_field_id = None

    def create_new_field(self, preset: Optional[str] = None) -> str:
        field_id = self.tab_manager.create_new_tab(preset)
        self.active_field_id = field_id
        self.qfc.initialize_field(field_id, preset=preset)
        return field_id

    def switch_to_field(self, field_id: str):
        if self.tab_manager.field_exists(field_id):
            self.active_field_id = field_id
            self.qfc.load_field(field_id)
        else:
            raise ValueError(f"Field '{field_id}' does not exist")

    def inject_scroll(self, scroll_id: str, target_field_id: Optional[str] = None):
        field_id = target_field_id or self.active_field_id
        if not field_id:
            raise RuntimeError("No active field to inject into")
        scroll_data = self.scroll_engine.fetch_scroll(scroll_id)
        self.qfc.inject_scroll(field_id, scroll_data)

    def run_engine(self, engine_type: str, field_id: Optional[str] = None, params: Optional[Dict] = None):
        field_id = field_id or self.active_field_id
        if not field_id:
            raise RuntimeError("No active field")
        engine_output = self.engine_dock.run(engine_type, field_id, params)
        self.qfc.apply_engine_output(field_id, engine_output)

    def save_current_session(self):
        if not self.active_field_id:
            return
        field_data = self.qfc.export_field(self.active_field_id)
        self.file_manager.save_session(field_id=self.active_field_id, data=field_data)

    def load_saved_session(self, field_id: str):
        data = self.file_manager.load_session(field_id)
        self.qfc.load_field_from_data(field_id, data)
        self.active_field_id = field_id

    def export_all_fields(self) -> Dict[str, Any]:
        export = {}
        for field_id in self.tab_manager.list_all_tabs():
            export[field_id] = self.qfc.export_field(field_id)
        return export

    def shutdown(self):
        self.save_current_session()
        self.scroll_engine.shutdown()
        self.qfc.shutdown()
        self.engine_dock.shutdown()
        self.tab_manager.shutdown()