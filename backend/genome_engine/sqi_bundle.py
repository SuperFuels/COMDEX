from __future__ import annotations

from typing import Any, Dict, List, Optional

# GX1-local, zero-coupling SQI bundle:
# - MUST be deterministic under TESSARIS_DETERMINISTIC_TIME=1
# - MUST NOT import QQC or heavy SQI subsystems
# - SHOULD accept either trace lines or a small derived signal series


def build_sqi_bundle(
    *,
    scenario_id: str,
    mode: str,
    seed: int = 0,
    channel: int | None = None,
    qscore_series: Optional[List[float]] = None,
    trace_events: Optional[List[Dict[str, Any]]] = None,
    **_extra: Any,
) -> Dict[str, Any]:
    q = list(qscore_series or [])

    # Minimal deterministic summary (no RNG, no wall clock)
    n = len(q)
    q_mean = float(sum(q) / n) if n else 0.0
    q_min = float(min(q)) if n else 0.0
    q_max = float(max(q)) if n else 0.0

    return {
        "trace_kind": "sqi_bundle",
        "scenario_id": str(scenario_id),
        "mode": str(mode),
        "seed": int(seed),
        "channel": int(channel) if channel is not None else 0,
        "n": int(n),
        "qscore_mean": q_mean,
        "qscore_min": q_min,
        "qscore_max": q_max,
        # Keep permissive for future expansion:
        "meta": {
            "source": "gx1_local",
            "has_trace_events": bool(trace_events),
        },
    }