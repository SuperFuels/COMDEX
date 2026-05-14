# File: backend/modules/sci/sci_serializer.py

import json
from datetime import datetime
from typing import Any, Dict, Optional, List
from pathlib import Path
import hashlib

SCI_CONTAINER_VERSION = "1.0"


def serialize_field_session(field_state: Dict[str, Any],
                             observer_id: Optional[str] = None,
                             active_plugins: Optional[List[str]] = None,
                             include_replay_log: bool = True) -> Dict[str, Any]:
    """
    Converts current QuantumFieldCanvas state into SCI-compatible .dc.json structure.
    """
    timestamp = datetime.utcnow().isoformat()
    session_id = hashlib.sha256(timestamp.encode()).hexdigest()[:10]

    container = {
        "version": SCI_CONTAINER_VERSION,
        "timestamp": timestamp,
        "container_id": session_id,
        "observer_id": observer_id or "unknown",
        "nodes": field_state.get("nodes", []),
        "links": field_state.get("links", []),
        "glyphs": field_state.get("glyphs", []),
        "scrolls": field_state.get("scrolls", []),
        "replay_log": field_state.get("replay_log") if include_replay_log else [],
        "qwaveBeams": field_state.get("qwaveBeams", []),
        "entanglement": field_state.get("entanglement", {}),
        "sqi_metrics": field_state.get("sqi_metrics", {}),
        "seed": {
            "observer_location": field_state.get("camera", {}).get("position", [0, 0, 10]),
            "scroll_position": field_state.get("scroll_position", 0),
            "active_plugins": active_plugins or [],
            "memory_trace_ids": field_state.get("memory_trace_ids", []),
            "qwave_trace_hash": field_state.get("qwave_trace_hash", ""),
        }
    }

    return container


def save_sci_container(container: Dict[str, Any], save_dir: str = "saved_sessions", name: Optional[str] = None) -> str:
    """
    Saves the given SCI container as a .dc.json file.
    """
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    
    if not name:
        timestamp = container.get("timestamp", datetime.utcnow().isoformat())
        name = timestamp.replace(":", "-").replace(".", "-")

    filename = f"{name}.dc.json"
    filepath = Path(save_dir) / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(container, f, indent=2)

    return str(filepath)


# ✅ Optional test run
if __name__ == "__main__":
    dummy_state = {
        "nodes": [{"id": "n1", "label": "idea()"}],
        "links": [],
        "glyphs": [],
        "scrolls": [],
        "camera": {"position": [0, 0, 10]},
        "scroll_position": 0,
        "memory_trace_ids": ["m123"],
        "qwave_trace_hash": "abc123",
    }
    container = serialize_field_session(dummy_state, observer_id="kevin", active_plugins=["C1", "C2"])
    path = save_sci_container(container)
    print(f"✅ Saved SCI session to: {path}")