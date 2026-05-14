# File: backend/modules/knowledge_graph/indexes/glyph_anchor_index.py

from typing import Dict, Optional, Any

# Glyph -> Environment Object mapping
GLYPH_ANCHOR_INDEX: Dict[str, Dict[str, Any]] = {}

def set_anchor(glyph_id: str, env_obj_id: str, anchor_type: str, coord: Optional[Dict[str, float]] = None) -> None:
    """
    Map a glyph ID to an environment object.
    """
    GLYPH_ANCHOR_INDEX[glyph_id] = {
        "env_obj_id": env_obj_id,
        "type": anchor_type,
        "coord": coord or {}
    }

def get_anchor(glyph_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve anchor metadata for a glyph ID.
    """
    return GLYPH_ANCHOR_INDEX.get(glyph_id)

def remove_anchor(glyph_id: str) -> None:
    """
    Remove an anchor mapping for a glyph ID.
    """
    if glyph_id in GLYPH_ANCHOR_INDEX:
        del GLYPH_ANCHOR_INDEX[glyph_id]

def list_anchors() -> Dict[str, Dict[str, Any]]:
    """
    List all glyph anchors.
    """
    return GLYPH_ANCHOR_INDEX