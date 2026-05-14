# ============================================================
# 📁 backend/modules/qfield/qfc_trigger_engine.py
# ============================================================

"""
QFCTriggerEngine - symbolic quantum field trigger manager.
Used by Tessaris QQC to execute and orchestrate QFC sheets (Symbolic Quantum Sheets)
in dynamic resonance contexts.
"""

import os
import json
import uuid
import logging
from typing import Dict, Any, Optional

# Base path for stored QFC sheets
QFC_SHEET_DIR = "backend/data/qfc_sheets"
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Low-Level Utility Functions (kept for reuse)
# ──────────────────────────────────────────────
def load_qfc_by_id(sheet_id: str) -> Dict[str, Any]:
    """
    Load a QFC sheet from disk given its ID.
    """
    filename = os.path.join(QFC_SHEET_DIR, f"{sheet_id}.sqs.json")
    if not os.path.exists(filename):
        raise FileNotFoundError(f"QFC sheet not found: {filename}")

    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def trigger_qfc_sheet(sheet: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Triggers a symbolic QFC sheet with optional runtime context.
    """
    sheet_type = sheet.get("type", "unknown")
    label = sheet.get("label", "Unnamed QFC Sheet")
    session_id = f"qfc_session_{uuid.uuid4().hex[:8]}"

    logger.info(f"[QFCTriggerEngine] Triggering QFC Sheet: {label} ({sheet_type}) -> Session ID: {session_id}")

    # Simulated execution result
    return {
        "session_id": session_id,
        "sheet_type": sheet_type,
        "label": label,
        "executed_with_context": context,
    }


# ──────────────────────────────────────────────
#  Class Wrapper for QQC Runtime Integration
# ──────────────────────────────────────────────
class QFCTriggerEngine:
    """
    High-level interface for managing, loading, and triggering
    QFC sheets during QQC runtime synchronization.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or QFC_SHEET_DIR
        self.last_session_id: Optional[str] = None
        self.last_result: Optional[Dict[str, Any]] = None
        logger.info(f"[QFCTriggerEngine] Initialized with base_dir={self.base_dir}")

    def load_sheet(self, sheet_id: str) -> Dict[str, Any]:
        """Load a QFC sheet by ID."""
        return load_qfc_by_id(sheet_id)

    def trigger(self, sheet_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Trigger a sheet by ID with optional context."""
        context = context or {}
        sheet = self.load_sheet(sheet_id)
        result = trigger_qfc_sheet(sheet, context)
        self.last_session_id = result.get("session_id")
        self.last_result = result
        return result

    def update_field_state(self, field_tensor: Any) -> None:
        """
        Optional hook called by QQC to update the QFC field tensor
        before running new triggers (placeholder for future physics layer).
        """
        logger.debug(f"[QFCTriggerEngine] Updating field tensor -> {str(field_tensor)[:80]}")

    def get_last_result(self) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent trigger result."""
        return self.last_result


# ──────────────────────────────────────────────
#  CLI Harness (Optional Debugging)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="🧠 Test QFCTriggerEngine for a given sheet ID.")
    parser.add_argument("sheet_id", help="ID of the QFC sheet to trigger")
    parser.add_argument("--context", help="Optional JSON string for trigger context", default="{}")
    args = parser.parse_args()

    context = json.loads(args.context)
    engine = QFCTriggerEngine()
    result = engine.trigger(args.sheet_id, context)
    print(json.dumps(result, indent=2))