# File: backend/modules/glyphnet/glyphnet_trace.py

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Internal trace log
GLYPHNET_TRACE_BUFFER: List[Dict[str, Any]] = []

logger = logging.getLogger(__name__)

def log_trace_event(
    event_type: str,
    data: Dict[str, Any],
    tags: Optional[List[str]] = None
) -> None:
    """
    Log a trace event to the GlyphNet trace buffer with optional tags.
    """
    trace = {
        "event": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
        "tags": tags or []
    }
    GLYPHNET_TRACE_BUFFER.append(trace)

    # Limit trace buffer to last 200 items
    if len(GLYPHNET_TRACE_BUFFER) > 200:
        GLYPHNET_TRACE_BUFFER.pop(0)

    logger.debug(f"[GlyphNetTrace] {event_type}: {data} [tags: {tags}]")


# ✅ Awareness traces
def log_confidence_trace(data: Dict[str, Any]) -> None:
    log_trace_event("awareness_confidence", data, tags=["awareness", "confidence"])


def log_blindspot_trace(data: Dict[str, Any]) -> None:
    log_trace_event("awareness_blindspot", data, tags=["awareness", "blindspot"])


# ✅ Glyph execution traces
def log_glyph_execution(glyph_id: str, snapshot_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Log a glyph execution event, optionally linking it to a KG snapshot.
    """
    log_trace_event(
        "glyph_execution",
        {"glyph_id": glyph_id, "snapshot_id": snapshot_id, "metadata": metadata or {}},
        tags=["glyph", "execution"]
    )


# ✅ Reasoning/Reflection traces
def log_reasoning_trace(glyph_id: str, reasoning: str, snapshot_id: Optional[str] = None) -> None:
    """
    Log a reasoning/reflection event tied to a glyph.
    """
    log_trace_event(
        "glyph_reasoning",
        {"glyph_id": glyph_id, "reasoning": reasoning, "snapshot_id": snapshot_id},
        tags=["glyph", "reasoning"]
    )


# ✅ Prediction/Dream traces
def log_prediction_trace(glyph_id: str, predicted_path: List[str], snapshot_id: Optional[str] = None) -> None:
    """
    Log a predictive (dream) glyph path trace.
    """
    log_trace_event(
        "glyph_prediction",
        {"glyph_id": glyph_id, "predicted_path": predicted_path, "snapshot_id": snapshot_id},
        tags=["glyph", "prediction", "dream"]
    )


# ✅ KG Snapshot trace
def log_kg_snapshot(snapshot_id: str, node_count: int, link_count: int) -> None:
    """
    Log a Knowledge Graph snapshot event.
    """
    log_trace_event(
        "kg_snapshot",
        {"snapshot_id": snapshot_id, "nodes": node_count, "links": link_count},
        tags=["kg", "snapshot"]
    )


# ✅ Recent trace retrieval
def get_recent_traces(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieve the most recent trace events.
    """
    return GLYPHNET_TRACE_BUFFER[-limit:]


def clear_trace_log() -> None:
    """
    Clear all traces (for reset or tests).
    """
    GLYPHNET_TRACE_BUFFER.clear()