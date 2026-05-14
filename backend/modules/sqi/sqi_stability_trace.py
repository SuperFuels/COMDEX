"""
SQI Stability Curve Collector
Tracks ΔSQI events over time for cognitive stability + dream mode tuning.
"""

import time
import collections
from typing import Deque, Dict, Any, List

WINDOW = 300  # seconds (5 minutes history)

# ring buffer of (timestamp, delta)
_sqi_history: Deque[Dict[str, Any]] = collections.deque(maxlen=5000)

def record_sqi_delta(delta: float, source: str = "runtime"):
    evt = {
        "ts": time.time(),
        "delta": float(delta),
        "source": source
    }
    _sqi_history.append(evt)

def get_recent_stability_curve(seconds: int = WINDOW) -> List[Dict[str, Any]]:
    now = time.time()
    cutoff = now - seconds
    return [e for e in _sqi_history if e["ts"] >= cutoff]

def get_stability_score(seconds: int = WINDOW) -> float:
    """
    stability = low variance, small deltas
    return ~0..1 where 1 = calm, 0 = chaotic
    """
    data = get_recent_stability_curve(seconds)
    if not data:
        return 1.0

    deltas = [abs(e["delta"]) for e in data]
    avg = sum(deltas) / len(deltas)
    # inverse relationship (log-ish)
    stability = max(0.0, 1.0 - avg * 4.0)
    return round(stability, 4)