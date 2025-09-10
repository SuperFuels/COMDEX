import uuid
import json
from typing import List, Dict, Any
from .symbolic_pattern_engine import SymbolicPattern
from datetime import datetime


def inject_patterns(container: Dict[str, Any], patterns: List[SymbolicPattern]) -> Dict[str, Any]:
    """
    Inject symbolic patterns into the container's `.dc.json` structure.
    Adds/merges with existing patterns[] and appends pattern_trace[].
    """
    if "patterns" not in container:
        container["patterns"] = []

    if "pattern_trace" not in container:
        container["pattern_trace"] = []

    # Avoid duplicates by pattern_id
    existing_ids = {p.get("pattern_id") for p in container["patterns"]}

    for pattern in patterns:
        pattern_dict = pattern.to_dict()

        if pattern.pattern_id not in existing_ids:
            container["patterns"].append(pattern_dict)
            existing_ids.add(pattern.pattern_id)

        trace_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "pattern_id": pattern.pattern_id,
            "glyphs": pattern.glyphs,
            "context": pattern.source_container,
            "prediction": pattern.prediction,
            "sqi_score": pattern.sqi_score,
        }

        container["pattern_trace"].append(trace_entry)

    return container


def extract_patterns(container: Dict[str, Any]) -> List[SymbolicPattern]:
    """
    Extracts patterns[] from a .dc container and returns as SymbolicPattern instances.
    """
    return [
        SymbolicPattern.from_dict(p) for p in container.get("patterns", [])
    ]


def merge_pattern_traces(old: List[Dict], new: List[Dict]) -> List[Dict]:
    """
    Merge old and new pattern_trace[] entries, avoiding duplicates by pattern_id + timestamp.
    """
    seen = set()
    merged = []

    for trace in old + new:
        key = (trace.get("pattern_id"), trace.get("timestamp"))
        if key not in seen:
            seen.add(key)
            merged.append(trace)

    return sorted(merged, key=lambda x: x["timestamp"])


def save_container(container: Dict[str, Any], path: str):
    """
    Save the modified container to disk as .dc.json.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(container, f, indent=2)


def load_container(path: str) -> Dict[str, Any]:
    """
    Load a .dc.json container from disk.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)