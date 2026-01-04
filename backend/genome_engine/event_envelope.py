from __future__ import annotations

from typing import Any, Dict


def beam_event_envelope(
    *,
    tick: int,
    t: float,
    event_type: str,
    source: str,
    target: str,
    qscore: float,
    drift: float,
    scenario_id: str,
    channel: int,
    meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Canonical minimal trace envelope for SLE/Beam-mode GX1 runs.

    Keep this stable: it is the contract surface for TRACE.jsonl.
    """
    return {
        "trace_kind": "beam_event",
        "tick": int(tick),
        "t": float(t),
        "event_type": str(event_type),
        "source": str(source),
        "target": str(target),
        "qscore": float(qscore),
        "drift": float(drift),
        "scenario_id": str(scenario_id),
        "channel": int(channel),
        "meta": meta or {},
    }
