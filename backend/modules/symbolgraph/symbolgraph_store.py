# File: backend/modules/symbolgraph/symbolgraph_store.py

import logging
import time
from typing import Dict

# Simulated persistent store - in a real system, replace with DB hooks
SYMBOLGRAPH_MEASUREMENTS: Dict[str, list[dict]] = {}

logger = logging.getLogger(__name__)


def store_measurement_result(glyph_id: str, result: str, score: float):
    """
    Store a collapse measurement result into the SymbolGraph memory store.

    Args:
        glyph_id (str): Unique identifier of the glyph (or symbolic node).
        result (str): The observed collapse value or interpretation.
        score (float): Confidence score between 0.0 and 1.0.
    """
    if not glyph_id or not result:
        raise ValueError("Both glyph_id and result must be provided.")

    timestamp = time.time()
    entry = {
        "timestamp": timestamp,
        "result": result,
        "score": score
    }

    if glyph_id not in SYMBOLGRAPH_MEASUREMENTS:
        SYMBOLGRAPH_MEASUREMENTS[glyph_id] = []

    # Prevent duplicate measurements with the same result in a tight window
    recent_entries = SYMBOLGRAPH_MEASUREMENTS[glyph_id][-5:]
    for e in recent_entries:
        if e["result"] == result and abs(e["timestamp"] - timestamp) < 2.0:
            logger.info(f"[SymbolGraphStore] Duplicate measurement ignored for '{glyph_id}' -> {result}")
            return

    SYMBOLGRAPH_MEASUREMENTS[glyph_id].append(entry)
    logger.info(f"[SymbolGraphStore] ✅ Stored collapse: {glyph_id} -> {result} (score={score:.2f})")


def get_measurements(glyph_id: str) -> list[dict]:
    """
    Retrieve all stored measurement entries for a given glyph.

    Returns:
        List of dictionaries with keys: 'timestamp', 'result', 'score'.
    """
    return SYMBOLGRAPH_MEASUREMENTS.get(glyph_id, [])


def clear_measurements(glyph_id: str):
    """
    Erase all stored measurement history for a glyph.
    """
    if glyph_id in SYMBOLGRAPH_MEASUREMENTS:
        del SYMBOLGRAPH_MEASUREMENTS[glyph_id]
        logger.info(f"[SymbolGraphStore] 🧹 Cleared measurements for '{glyph_id}'")