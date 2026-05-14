from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict


SCHEMA = "AION.Forecast.v1"


def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


def _path() -> Path:
    return _data_root() / "telemetry" / "forecast_report.jsonl"


def append_forecast(*, ts: float | None, session: str, goal: str, rho_next: float, sqi_next: float, confidence: float) -> None:
    rec: Dict[str, Any] = {
        "ts": float(ts if ts is not None else time.time()),
        "session": (session or "").strip(),
        "goal": (goal or "maintain_coherence").strip(),
        "rho_next": float(rho_next),
        "sqi_next": float(sqi_next),
        "confidence": float(confidence),
        "schema": SCHEMA,
    }
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")