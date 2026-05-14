# File: backend/modules/sci/sci_loader.py

import json
from typing import Dict, Any, Optional
from pathlib import Path

def load_sci_container(path: str) -> Optional[Dict[str, Any]]:
    """
    Loads a .dc.json SCI container from disk.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"📥 Loaded SCI container from: {path}")
        return data
    except Exception as e:
        print(f"❌ Failed to load SCI container '{path}': {e}")
        return None

def extract_field_state(container: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts QuantumFieldCanvas-compatible field state from loaded SCI container.
    """
    field_state = {
        "nodes": container.get("nodes", []),
        "links": container.get("links", []),
        "glyphs": container.get("glyphs", []),
        "scrolls": container.get("scrolls", []),
        "replay_log": container.get("replay_log", []),
        "qwaveBeams": container.get("qwaveBeams", []),
        "entanglement": container.get("entanglement", {}),
        "sqi_metrics": container.get("sqi_metrics", {}),
        "memory_trace_ids": container.get("seed", {}).get("memory_trace_ids", []),
        "qwave_trace_hash": container.get("seed", {}).get("qwave_trace_hash"),
        "scroll_position": container.get("seed", {}).get("scroll_position", 0),
        "camera": {
            "position": container.get("seed", {}).get("observer_location", [0, 0, 10])
        }
    }
    return field_state

# Optional test run
if __name__ == "__main__":
    sample_file = "saved_sessions/test_session.dc.json"
    container = load_sci_container(sample_file)
    if container:
        field_state = extract_field_state(container)
        print(f"✅ Extracted field state with {len(field_state['nodes'])} nodes.")
