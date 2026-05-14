# File: backend/modules/patterns/pattern_qfc_bridge.py

from typing import Dict, Any, Optional
from backend.modules.patterns.pattern_registry import PatternRegistry
from backend.modules.qfield.qfc_trigger_engine import trigger_qfc_sheet
from backend.modules.qfield.qfc_utils import load_qfc_by_id

class PatternQFCBridge:
    """
    Bridges symbolic patterns with QFC activation.
    Triggers Quantum Field Canvas simulations or overlays when symbolic patterns are detected.
    """

    def __init__(self):
        self.registry = PatternRegistry()

    def trigger_qfc_from_pattern(self, pattern: Dict[str, Any], container: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Triggers a QFC simulation based on the detected symbolic pattern.
        Returns the QFC session ID or None if skipped.
        """
        glyphs = pattern.get("glyphs", [])
        trigger_logic = pattern.get("trigger_logic", "")
        pattern_id = pattern.get("pattern_id", "")
        container_id = container.get("id") if container else None

        # Load sheet ID from pattern metadata
        sheet_id = pattern.get("metadata", {}).get("trigger_sheet_id")
        if not sheet_id:
            return None  # Nothing to trigger

        try:
            sheet = load_qfc_by_id(sheet_id)
        except FileNotFoundError:
            return None

        context = {
            "glyph_sequence": glyphs,
            "pattern_id": pattern_id,
            "trigger_logic": trigger_logic,
            "container_id": container_id,
            "sqi_score": pattern.get("sqi_score", 0.0),
        }

        result = trigger_qfc_sheet(sheet, context)
        return result.get("session_id")