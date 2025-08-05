"""
📦 Collapse Trace Exporter
--------------------------------------
Exports HyperdriveEngine or SQI runtime state snapshots into `.dc.json`
format for symbolic replay, GHX visualization, or entanglement analysis.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any

EXPORT_DIR = "data/collapse_traces"
os.makedirs(EXPORT_DIR, exist_ok=True)

def export_collapse_trace(state: Dict[str, Any], filename: str = None) -> str:
    """
    Export a collapse trace to disk in `.dc.json` format.
    
    Args:
        state (dict): Engine or SQI state dictionary.
        filename (str, optional): Custom filename (without extension).
    
    Returns:
        str: Full path to the saved file.
    """
    if filename is None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"collapse_trace_{timestamp}.dc.json"

    filepath = os.path.join(EXPORT_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(state, f, indent=4)

    print(f"💾 Collapse trace exported: {filepath}")
    return filepath


def load_collapse_trace(filename: str) -> Dict[str, Any]:
    """
    Load a previously exported collapse trace from disk.
    
    Args:
        filename (str): Filename or path to `.dc.json` trace.
    
    Returns:
        dict: Loaded trace state.
    """
    filepath = filename if os.path.exists(filename) else os.path.join(EXPORT_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Collapse trace not found: {filepath}")

    with open(filepath, "r") as f:
        trace = json.load(f)

    print(f"📂 Collapse trace loaded: {filepath}")
    return trace