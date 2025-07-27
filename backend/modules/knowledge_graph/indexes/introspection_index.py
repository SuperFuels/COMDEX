# File: backend/modules/knowledge_graph/indexes/introspection_index.py

"""
🌀 Introspection Index
Tracks system-generated thoughts, contradictions, confidence drops, blindspots,
and other internal reasoning traces across Codex, AION, DreamCore, and GlyphNet.

Usage:
  - awareness_engine.py → add_introspection_event(...)
  - codex_executor.py → log_glyph_reflections(...)
  - dreamcore.py → record_dream_trace(...)
"""

import datetime
from typing import Optional, Dict, Any
from backend.modules.state_manager import get_active_container
from backend.modules.utils.time_utils import get_current_timestamp
from backend.modules.utils.id_utils import generate_uuid
import hashlib

INDEX_NAME = "introspection_index"

def _get_or_create_index(container: Dict[str, Any], index_name: str):
    if "indexes" not in container:
        container["indexes"] = {}
    if index_name not in container["indexes"]:
        container["indexes"][index_name] = []
    return container["indexes"][index_name]

def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()

def add_introspection_event(
    description: str,
    source_module: str,
    tags: Optional[list] = None,
    confidence: Optional[float] = None,
    blindspot_trigger: Optional[str] = None,
    glyph_trace_ref: Optional[str] = None,
    persona_state: Optional[str] = None
) -> str:
    """
    Adds a symbolic introspection event to the knowledge graph index.

    Args:
        description: Human-readable insight or reflection.
        source_module: Name of the component generating this entry.
        tags: Optional list of logic/emotion/identity tags.
        confidence: Optional float [0–1] indicating introspective certainty.
        blindspot_trigger: Optional label that caused this awareness.
        glyph_trace_ref: Optional ID reference to glyph trace.
        persona_state: Optional identity/personality context string.

    Returns:
        UUID of the index entry.
    """
    container = get_active_container()
    event_id = generate_uuid()
    timestamp = get_current_timestamp()

    entry = {
        "id": event_id,
        "type": "introspection",
        "description": description,
        "hash": _hash_content(description),
        "timestamp": timestamp,
        "source": source_module,
        "tags": tags or [],
        "confidence": confidence,
        "blindspot_trigger": blindspot_trigger,
        "glyph_trace": glyph_trace_ref,
        "persona": persona_state,
    }

    index = _get_or_create_index(container, INDEX_NAME)
    index.append(entry)
    container["last_index_update"] = datetime.datetime.utcnow().isoformat()

    return event_id