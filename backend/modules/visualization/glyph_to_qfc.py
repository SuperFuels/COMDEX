# 📁 backend/modules/visualization/glyph_to_qfc.py

"""
🎯 Glyph → QFC Payload Converter
────────────────────────────────────────
Converts executed glyphs and entangled wave logic into QFC canvas format:
  - nodes: visual glyph or beam representations
  - links: connections between symbolic entities
Used for real-time WebSocket broadcasting.
"""

from typing import Dict, List, Any
from uuid import uuid4
import time

def to_qfc_payload(glyph: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Converts a single glyph execution result into a QFC WebSocket payload.
    """
    container_id = context.get("container_id", "unknown")
    timestamp = time.time()
    node_id = f"qfc_node_{uuid4().hex[:8]}"
    source_node = context.get("source_node", None)

    node = {
        "id": node_id,
        "label": glyph.get("glyph", "∅"),
        "type": "glyph",
        "container": container_id,
        "metadata": {
            "context": context,
            "timestamp": timestamp
        },
        "style": {
            "color": "#b3e5fc",
            "size": 12,
            "highlight": True
        }
    }

    link = {
        "source": source_node or "origin",
        "target": node_id,
        "type": "execution",
        "label": glyph.get("op", "→"),
        "metadata": {
            "container": container_id,
            "timestamp": timestamp
        },
        "style": {
            "color": "#81d4fa",
            "width": 2
        }
    }

    return {
        "nodes": [node],
        "links": [link]
    }