# -*- coding: utf-8 -*-
# File: backend/modules/knowledge_graph/indexes/introspection_index.py

"""
🌀 Introspection Index
Tracks system-generated thoughts, contradictions, confidence drops, blindspots,
predictions, and internal reasoning traces across Codex, AION, DreamCore, and GlyphNet.

Usage:
  - awareness_engine.py → add_introspection_event(...)
  - codex_executor.py → add_introspection_event(...)
  - dreamcore.py → record_dream_trace(...)
  - predictive_glyph_composer.py → log_predictive_fork(...)
"""

from __future__ import annotations

import datetime
import hashlib
from typing import Optional, Dict, Any

# ✅ Pull active state from your runtime (unchanged import path)
from backend.modules.consciousness.state_manager import STATE
from backend.modules.knowledge_graph.time_utils import get_current_timestamp
from backend.modules.knowledge_graph.id_utils import generate_uuid

INDEX_NAME = "introspection_index"

# ─────────────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────────────

def _get_or_create_index(container: Dict[str, Any], index_name: str):
    """
    Ensure the container has an 'indexes' dict and a list for `index_name`.
    Safe to call even if container is an empty dict.
    """
    if "indexes" not in container or not isinstance(container.get("indexes"), dict):
        container["indexes"] = {}
    if index_name not in container["indexes"] or not isinstance(container["indexes"].get(index_name), list):
        container["indexes"][index_name] = []
    return container["indexes"][index_name]

def _hash_content(content: str) -> str:
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()

def _safe_get_active_container() -> Dict[str, Any]:
    """
    Robustly fetch the active container dict.
    Tries (in order):
      1) STATE.get_current_container()
      2) STATE.current_container
      3) STATE.get_active_universal_container_system().get("active_container")
    Returns {} if none available so callers can still append to a scratch structure.
    """
    # 1) Preferred helper
    try:
        if hasattr(STATE, "get_current_container") and callable(STATE.get_current_container):
            c = STATE.get_current_container()
            if isinstance(c, dict):
                return c
    except Exception:
        pass

    # 2) Direct attribute
    try:
        c = getattr(STATE, "current_container", None)
        if isinstance(c, dict):
            return c
    except Exception:
        pass

    # 3) UCS wrapper
    try:
        if hasattr(STATE, "get_active_universal_container_system") and callable(STATE.get_active_universal_container_system):
            ucs = STATE.get_active_universal_container_system()  # bound method, no args
            if isinstance(ucs, dict):
                c = ucs.get("active_container")
                if isinstance(c, dict):
                    return c
    except Exception:
        pass

    # 4) Graceful empty fallback (prevents NoneType errors)
    return {}

# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_active_container() -> Dict[str, Any]:
    """
    Backward-compatible accessor used by other modules.
    Returns {} if no active container is available.
    """
    return _safe_get_active_container()

def add_introspection_event(
    description: str,
    source_module: str,
    tags: Optional[list] = None,
    confidence: Optional[float] = None,
    blindspot_trigger: Optional[str] = None,
    glyph_trace_ref: Optional[str] = None,
    persona_state: Optional[str] = None,
    prediction_meta: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Adds a symbolic introspection or prediction event to the knowledge graph index.

    Args:
        description: Human-readable insight or reflection.
        source_module: Name of the component generating this entry.
        tags: Optional list of logic/emotion/identity tags.
        confidence: Optional float [0–1] indicating introspective certainty.
        blindspot_trigger: Optional label that caused this awareness.
        glyph_trace_ref: Optional ID reference to glyph trace.
        persona_state: Optional identity/personality context string.
        prediction_meta: Optional dict with predictive fork metadata
                         (fork_id, outcome, cost_estimate, etc.).

    Returns:
        UUID of the index entry.
    """
    container = _safe_get_active_container()
    event_id = generate_uuid()
    timestamp = get_current_timestamp()

    entry = {
        "id": event_id,
        "type": "introspection" if prediction_meta is None else "prediction",
        "description": description,
        "hash": _hash_content(description),
        "timestamp": timestamp,
        "source": source_module,
        "tags": tags or [],
        "confidence": confidence,
        "blindspot_trigger": blindspot_trigger,
        "glyph_trace": glyph_trace_ref,
        "persona": persona_state,
        "prediction_meta": prediction_meta or None,
    }

    index = _get_or_create_index(container, INDEX_NAME)
    index.append(entry)
    container["last_index_update"] = datetime.datetime.utcnow().isoformat()

    return event_id

# 🔮 Convenience hook for predictive forks
def log_predictive_fork(
    fork: Dict[str, Any],
    container_id: str,
    source: str = "predictive_glyph_composer"
):
    """
    Logs a predictive fork event into the introspection index.
    Automatically hashes the fork and stores metadata for replay.
    """
    description = f"🔮 Predicted fork: {fork.get('glyph')} → {fork.get('outcome', 'unknown outcome')}"
    prediction_meta = {
        "fork_id":    fork.get("id"),
        "glyph":      fork.get("glyph"),
        "goal":       fork.get("goal"),
        "outcome":    fork.get("outcome"),
        "confidence": fork.get("confidence"),
        "cost_estimate": fork.get("cost_estimate"),
        "container_id":  container_id,
    }
    return add_introspection_event(
        description=description,
        source_module=source,
        tags=["prediction", "introspection"],
        confidence=fork.get("confidence"),
        glyph_trace_ref=fork.get("glyph"),
        prediction_meta=prediction_meta,
    )