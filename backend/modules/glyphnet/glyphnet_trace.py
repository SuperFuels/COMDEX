# File: backend/modules/glyphnet/glyphnet_trace.py

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Internal trace buffer
# ──────────────────────────────────────────────
GLYPHNET_TRACE_BUFFER: List[Dict[str, Any]] = []
TRACE_LIMIT = 200

# ──────────────────────────────────────────────
# Trace handler registry
# ──────────────────────────────────────────────
TraceHandler = Callable[[Dict[str, Any]], None]
TRACE_REGISTRY: Dict[str, TraceHandler] = {}


def register_trace_handler(event_type: str, handler: TraceHandler) -> None:
    """
    Register a custom handler for a specific trace event type.
    Handlers receive the trace dict after it is created.
    """
    TRACE_REGISTRY[event_type] = handler
    logger.info(f"[GlyphNetTrace] Registered handler for event: {event_type}")


# ──────────────────────────────────────────────
# Core logging
# ──────────────────────────────────────────────
def log_trace_event(
    event_type: str,
    data: Dict[str, Any],
    tags: Optional[List[str]] = None
) -> None:
    """
    Log a trace event to the GlyphNet trace buffer with optional tags.
    Dispatches to any registered handler for this event type.
    """
    trace = {
        "event": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
        "tags": tags or []
    }
    GLYPHNET_TRACE_BUFFER.append(trace)

    # Enforce buffer limit
    if len(GLYPHNET_TRACE_BUFFER) > TRACE_LIMIT:
        GLYPHNET_TRACE_BUFFER.pop(0)

    # Dispatch to handler if present
    handler = TRACE_REGISTRY.get(event_type)
    if handler:
        try:
            handler(trace)
        except Exception as e:
            logger.warning(f"[GlyphNetTrace] Handler for {event_type} failed: {e}")

    logger.debug(f"[GlyphNetTrace] {event_type}: {data} [tags: {tags}]")


# ──────────────────────────────────────────────
# Predefined event helpers
# ──────────────────────────────────────────────
def log_confidence_trace(data: Dict[str, Any]) -> None:
    log_trace_event("awareness_confidence", data, tags=["awareness", "confidence"])


def log_blindspot_trace(data: Dict[str, Any]) -> None:
    log_trace_event("awareness_blindspot", data, tags=["awareness", "blindspot"])


def log_glyph_execution(
    glyph_id: str,
    snapshot_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    log_trace_event(
        "glyph_execution",
        {"glyph_id": glyph_id, "snapshot_id": snapshot_id, "metadata": metadata or {}},
        tags=["glyph", "execution"]
    )


def log_reasoning_trace(
    glyph_id: str,
    reasoning: str,
    snapshot_id: Optional[str] = None
) -> None:
    log_trace_event(
        "glyph_reasoning",
        {"glyph_id": glyph_id, "reasoning": reasoning, "snapshot_id": snapshot_id},
        tags=["glyph", "reasoning"]
    )


def log_prediction_trace(
    glyph_id: str,
    predicted_path: List[str],
    snapshot_id: Optional[str] = None
) -> None:
    log_trace_event(
        "glyph_prediction",
        {"glyph_id": glyph_id, "predicted_path": predicted_path, "snapshot_id": snapshot_id},
        tags=["glyph", "prediction", "dream"]
    )


def log_kg_snapshot(
    snapshot_id: str,
    node_count: int,
    link_count: int
) -> None:
    log_trace_event(
        "kg_snapshot",
        {"snapshot_id": snapshot_id, "nodes": node_count, "links": link_count},
        tags=["kg", "snapshot"]
    )


# ──────────────────────────────────────────────
# Accessors
# ──────────────────────────────────────────────
def get_recent_traces(limit: int = 100) -> List[Dict[str, Any]]:
    return GLYPHNET_TRACE_BUFFER[-limit:]


def clear_trace_log() -> None:
    GLYPHNET_TRACE_BUFFER.clear()
    logger.info("[GlyphNetTrace] Trace buffer cleared")