# File: backend/modules/patterns/pattern_qfc_triggers.py

from backend.modules.patterns.pattern_registry import PatternRegistry
from backend.modules.qfield.qfc_trigger_engine import trigger_qfc_sheet
from backend.modules.qfield.qfc_utils import load_qfc_by_id

class PatternQFCBridge:
    """
    Links detected symbolic patterns to FlowSheet or AtomSheet logic containers.
    """

    def __init__(self):
        self.registry = PatternRegistry()

    def trigger_sheet_for_pattern(self, pattern_id: str, context: dict) -> dict:
        """
        Loads the QFC sheet linked to the pattern and runs it with the given context.
        """
        pattern = self.registry.get(pattern_id)
        if not pattern:
            return {"error": "Pattern not found."}

        sheet_id = pattern.metadata.get("trigger_sheet_id")
        if not sheet_id:
            return {"info": "No QFC trigger linked for this pattern."}

        sheet = load_qfc_by_id(sheet_id)
        result = trigger_qfc_sheet(sheet, context)
        return {"triggered": True, "sheet_id": sheet_id, "result": result}

    def bind_trigger_to_pattern(self, pattern_id: str, sheet_id: str):
        """
        Annotates the pattern with a QFC trigger ID.
        """
        pattern = self.registry.get(pattern_id)
        if pattern:
            pattern.metadata["trigger_sheet_id"] = sheet_id
            self.registry.register(pattern)