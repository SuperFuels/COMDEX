import json
from typing import List, Dict

def parse_ghost_for_overlay(trace_json: str) -> List[Dict]:
    """
    Convert ghost trace into simplified overlay events for GHX HUD replay.
    Each event includes: node_id, timestamp, glyph, emotion, entanglement.
    """
    try:
        trace = json.loads(trace_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid ghost JSON trace: {e}")

    overlays = []
    for entry in trace.get("replay", []):
        overlays.append({
            "node_id": entry.get("node_id"),
            "timestamp": entry.get("timestamp"),
            "glyph": entry.get("glyph", "↯"),
            "emotion": entry.get("emotion", "neutral"),
            "entanglement": entry.get("entanglement", []),
        })

    return overlays