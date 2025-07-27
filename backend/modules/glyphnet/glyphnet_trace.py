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

def log_confidence_trace(data: Dict[str, Any]) -> None:
    log_trace_event("awareness_confidence", data, tags=["awareness", "confidence"])

def log_blindspot_trace(data: Dict[str, Any]) -> None:
    log_trace_event("awareness_blindspot", data, tags=["awareness", "blindspot"])

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