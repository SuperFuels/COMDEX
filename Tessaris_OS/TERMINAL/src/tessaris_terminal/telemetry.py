from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class TelemetryWriter:
    """
    Writes telemetry.jsonl (one JSON object per timestep).
    Intended to be called inside sim loops, optionally.
    """
    path: Path
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.enabled:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # truncate on start
            self.path.write_text("")

    def write(self, rec: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")


def default_rec(*, t: int, controller: str, action: Optional[Dict[str, float]] = None,
                metrics: Optional[Dict[str, float]] = None, **extra: Any) -> Dict[str, Any]:
    rec: Dict[str, Any] = {"t": int(t), "controller": str(controller)}
    if action is not None:
        rec["action"] = action
    if metrics is not None:
        rec["metrics"] = metrics
    if extra:
        rec.update(extra)
    return rec
