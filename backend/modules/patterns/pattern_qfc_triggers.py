# File: backend/modules/patterns/pattern_qfc_triggers.py

from typing import Dict, Any, List
from backend.modules.patterns.pattern_registry import PatternRegistry
from backend.modules.qfield.qfc_trigger_engine import trigger_qfc_sheet
from backend.modules.qfield.qfc_utils import load_qfc_by_id

class PatternQFCBridge:
    """
    Links detected symbolic patterns to QFC Sheets (AtomSheets, FlowSheets).
    Triggers symbolic execution when a pattern context is matched.
    """

    def __init__(self):
        self.registry = PatternRegistry()

    def trigger_sheet_for_pattern(self, pattern_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Loads the QFC sheet linked to the given pattern and executes it with context.
        Returns the execution result or error.
        """
        pattern = self.registry.get(pattern_id)
        if not pattern:
            return {"error": f"Pattern not found: {pattern_id}"}

        sheet_id = pattern.metadata.get("trigger_sheet_id")
        if not sheet_id:
            return {"info": f"No QFC sheet bound to pattern {pattern_id}."}

        try:
            sheet = load_qfc_by_id(sheet_id)
            result = trigger_qfc_sheet(sheet, context)
            return {
                "triggered": True,
                "pattern_id": pattern_id,
                "sheet_id": sheet_id,
                "result": result
            }
        except Exception as e:
            return {"error": str(e), "pattern_id": pattern_id, "sheet_id": sheet_id}

    def bind_trigger_to_pattern(self, pattern_id: str, sheet_id: str) -> Dict[str, Any]:
        """
        Binds a QFC sheet (by ID) to a pattern for future triggering.
        """
        pattern = self.registry.get(pattern_id)
        if not pattern:
            return {"error": f"Pattern not found: {pattern_id}"}

        pattern.metadata["trigger_sheet_id"] = sheet_id
        self.registry.register(pattern)
        return {
            "success": True,
            "pattern_id": pattern_id,
            "trigger_sheet_id": sheet_id
        }

    def trigger_all_linked_patterns(self, patterns: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Triggers all QFC sheets linked to the given pattern list.
        Returns a list of execution results.
        """
        results = []
        for p in patterns:
            pid = p.get("id") or p.get("pattern_id")
            if pid:
                res = self.trigger_sheet_for_pattern(pid, context)
                results.append(res)
        return results

# Singleton
pattern_qfc_bridge = PatternQFCBridge()