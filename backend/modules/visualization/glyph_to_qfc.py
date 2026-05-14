# 📁 backend/modules/visualization/glyph_to_qfc.py

"""
🎯 Glyph -> QFC Payload Converter
────────────────────────────────────────
Converts executed glyphs and entangled wave logic into QFC canvas format:
  - nodes: visual glyph or beam representations
  - links: connections between symbolic entities
Used for real-time WebSocket broadcasting and symbolic replay.
"""

from typing import Dict, List, Any
from uuid import uuid4
import time
from typing import Optional

def to_qfc_payload(glyph: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Converts a single glyph execution result into a QFC WebSocket payload.
    Returns a dictionary with 'nodes' and 'links' for canvas injection.
    """

    timestamp = time.time()
    container_id = context.get("container_id", "unknown")
    source_node = context.get("source_node", "origin")
    source_glyph = context.get("source_glyph", None)

    # Glyph and beam ID fallback
    glyph_symbol = glyph.get("glyph", "∅")
    glyph_id = glyph.get("glyph_id", None)
    beam_id = glyph.get("beam_id", None)

    # Generate unique node ID
    node_id = glyph_id or f"qfc_node_{uuid4().hex[:8]}"

    # ─────────────────────────────────────────────
    # 🌐 Node (Glyph Execution Visualization)
    # ─────────────────────────────────────────────
    node = {
        "id": node_id,
        "label": glyph_symbol,
        "type": glyph.get("type", "glyph"),  # e.g., 'glyph', 'beam', 'projection'
        "container": container_id,
        "metadata": {
            "context": context,
            "timestamp": timestamp,
            "entropy": glyph.get("entropy"),
            "confidence": glyph.get("confidence"),
            "emotion": glyph.get("emotion_tag"),
            "beam_id": beam_id,
            "glyph_id": glyph_id,
            "origin": glyph.get("origin"),
            "source_glyph": source_glyph
        },
        "style": {
            "color": _get_color_by_emotion(glyph.get("emotion_tag")),
            "size": glyph.get("size", 12),
            "highlight": True,
            "shape": glyph.get("shape", "circle")
        }
    }

    # ─────────────────────────────────────────────
    # 🔗 Link (Connection to Prior Node / Beam)
    # ─────────────────────────────────────────────
    link = {
        "source": source_node,
        "target": node_id,
        "type": glyph.get("link_type", "execution"),
        "label": glyph.get("op", "->"),
        "metadata": {
            "timestamp": timestamp,
            "container": container_id,
            "beam_id": beam_id
        },
        "style": {
            "color": "#81d4fa",
            "width": 2,
            "style": "solid"
        }
    }

    return {
        "nodes": [node],
        "links": [link]
    }


# ─────────────────────────────────────────────
# 🎨 Emotion -> Color Mapping
# ─────────────────────────────────────────────
def _get_color_by_emotion(emotion: Optional[str]) -> str:
    """
    Return a HEX color based on symbolic emotion tag.
    Defaults to soft blue.
    """
    emotion_colors = {
        "curiosity": "#b3e5fc",
        "fear": "#ef9a9a",
        "joy": "#fff59d",
        "focus": "#aed581",
        "sadness": "#90caf9",
        "confusion": "#ce93d8",
        "anger": "#ef5350",
        "trust": "#a5d6a7",
        "wonder": "#ffcc80"
    }
    return emotion_colors.get(emotion, "#b3e5fc")  # default: soft blue