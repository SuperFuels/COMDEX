# File: backend/modules/glyphnet/glyphnet_trace.py

import logging
from datetime import datetime
from typing import Dict, Any, List

# Internal trace log
GLYPHNET_TRACE_BUFFER: List[Dict[str, Any]] = []

logger = logging.getLogger(__name__)

def log_trace_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Log a trace event to the GlyphNet trace buffer.
    """
    trace = {
        "event": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    GLYPHNET_TRACE_BUFFER.append(trace)

    # Limit trace buffer to last 200 items
    if len(GLYPHNET_TRACE_BUFFER) > 200:
        GLYPHNET_TRACE_BUFFER.pop(0)

    logger.debug(f"[GlyphNetTrace] {event_type}: {data}")

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