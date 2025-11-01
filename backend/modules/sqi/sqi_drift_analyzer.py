"""
sqi_drift_analyzer.py

Analyzes symbolic drift patterns across beam mutations or container evolutions.
Supports entropy deltas, trust shifts, coherence decay, and symbolic fingerprinting.
"""

import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 🧠 Internal memory store for per-beam drift snapshots
DRIFT_MEMORY: Dict[str, Dict[str, Any]] = {}

# 🚦 Stability threshold config
STABILITY_THRESHOLDS = {
    "entropy": 0.05,
    "trust": 0.05,
    "coherence": 0.10,
}


def analyze_drift_patterns(current_beam: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares the current beam state against its previous state and detects symbolic drift.

    Args:
        current_beam: The current symbolic beam dictionary.

    Returns:
        Dict with drift metrics:
            - entropy_drift
            - trust_shift
            - coherence_delta
            - time_delta_sec
            - is_stable
            - message (optional)
    """
    beam_id = current_beam.get("id", "unknown")
    now = time.time()

    current_meta = current_beam.get("symbolic_metadata", {})
    current_qscore = current_beam.get("qscore_metrics", {}).get("qscore", 0.0)

    prev = DRIFT_MEMORY.get(beam_id)

    # Update memory before early exit
    DRIFT_MEMORY[beam_id] = {
        "timestamp": now,
        "metadata": current_meta,
        "qscore": current_qscore,
    }

    if not prev:
        logger.info(f"[DriftAnalyzer] No prior state for beam '{beam_id}'")
        return {
            "entropy_drift": 0.0,
            "trust_shift": 0.0,
            "coherence_delta": 0.0,
            "time_delta_sec": 0.0,
            "is_stable": True,
            "message": "🆕 First-time drift analysis.",
        }

    dt = now - prev["timestamp"]
    prev_meta = prev.get("metadata", {})
    prev_qscore = prev.get("qscore", 0.0)

    # Core metric shifts
    entropy_drift = float(current_meta.get("entropy", 0)) - float(prev_meta.get("entropy", 0))
    trust_shift = float(current_meta.get("trust_score", 0)) - float(prev_meta.get("trust_score", 0))
    coherence_delta = float(current_qscore) - float(prev_qscore)

    # Stability detection
    is_stable = (
        abs(entropy_drift) < STABILITY_THRESHOLDS["entropy"] and
        abs(trust_shift) < STABILITY_THRESHOLDS["trust"] and
        abs(coherence_delta) < STABILITY_THRESHOLDS["coherence"]
    )

    result = {
        "entropy_drift": round(entropy_drift, 4),
        "trust_shift": round(trust_shift, 4),
        "coherence_delta": round(coherence_delta, 4),
        "time_delta_sec": round(dt, 2),
        "is_stable": is_stable,
    }

    logger.info(f"[DriftAnalyzer] Beam '{beam_id}' drift analysis -> {result}")
    return result


# Optional: Reset drift memory for all or specific beams
def reset_drift_memory(beam_id: Optional[str] = None) -> None:
    if beam_id:
        DRIFT_MEMORY.pop(beam_id, None)
        logger.info(f"[DriftAnalyzer] Drift memory reset for beam '{beam_id}'")
    else:
        DRIFT_MEMORY.clear()
        logger.info("[DriftAnalyzer] Drift memory fully reset.")