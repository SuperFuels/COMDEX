# File: backend/modules/sqi/qglyph_trace_logger.py

import time
import logging
from typing import Optional, Dict

from ..hexcore.memory_engine import store_memory

logger = logging.getLogger(__name__)

def log_qglyph_resolution(
    qglyph_id: str,
    observer_id: Optional[str],
    bias_score_left: float,
    bias_score_right: float,
    chosen_path: str,
    reason: Optional[str] = None,
    meta: Optional[Dict] = None
):
    """
    Logs a QGlyph collapse decision with observer bias and reasoning.
    Stores to memory engine and console log.
    """
    timestamp = int(time.time())

    trace = {
        "type": "qglyph_collapse_trace",
        "timestamp": timestamp,
        "qglyph_id": qglyph_id,
        "observer_id": observer_id,
        "bias_left": bias_score_left,
        "bias_right": bias_score_right,
        "chosen_path": chosen_path,
        "reason": reason or "",
        "meta": meta or {},
    }

    # Store in memory system for retrieval or review
    store_memory(trace)

    # Console log for monitoring
    logger.info(f"[QGlyph Collapse] ID: {qglyph_id} by {observer_id or 'Unknown'} → {chosen_path} (L:{bias_score_left:.2f}, R:{bias_score_right:.2f}) Reason: {reason}")

    return trace