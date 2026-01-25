# backend/modules/aion_cognition/goal_transitions.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

SCHEMA = "AION.GoalTransition.v1"


def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


def _log_path() -> Path:
    return _data_root() / "telemetry" / "goal_transition_log.jsonl"


def log_goal_transition(*, ts: float, from_goal: str, to_goal: str, cause: str, session: str) -> None:
    # Log on change only (caller can also enforce; we enforce here too)
    if (from_goal or "").strip() == (to_goal or "").strip():
        return

    rec: Dict[str, Any] = {
        "ts": float(ts),
        "from_goal": (from_goal or "").strip(),
        "to_goal": (to_goal or "").strip(),
        "cause": (cause or "").strip(),
        "session": (session or "").strip(),
        "schema": SCHEMA,
    }

    p = _log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")