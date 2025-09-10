# backend/modules/qfield/qfc_trigger_engine.py

import os
import json
import uuid
from typing import Dict, Any

# Base path for stored QFC sheets
QFC_SHEET_DIR = "backend/data/qfc_sheets"

def load_qfc_by_id(sheet_id: str) -> Dict[str, Any]:
    """
    Loads a QFC sheet by its ID from disk.
    """
    filename = os.path.join(QFC_SHEET_DIR, f"{sheet_id}.sqs.json")
    if not os.path.exists(filename):
        raise FileNotFoundError(f"QFC sheet not found: {filename}")
    
    with open(filename, "r") as f:
        return json.load(f)

def trigger_qfc_sheet(sheet: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Triggers a symbolic QFC sheet with optional context.
    Simulates execution and returns a result dict.
    """
    sheet_type = sheet.get("type", "unknown")
    label = sheet.get("label", "Unnamed QFC Sheet")
    session_id = f"qfc_session_{uuid.uuid4().hex[:8]}"

    # Simulate a basic trigger execution
    print(f"[QFCTriggerEngine] Triggering QFC Sheet: {label} ({sheet_type}) → Session ID: {session_id}")
    return {
        "session_id": session_id,
        "sheet_type": sheet_type,
        "label": label,
        "executed_with_context": context
    }