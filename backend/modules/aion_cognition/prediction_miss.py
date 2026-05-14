from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))

PRED_MISS_PATH = _data_root() / "telemetry" / "prediction_miss_log.jsonl"

SCHEMA = "AION.PredictionMiss.v1"

def append_prediction_miss(
    *,
    ts: float,
    session: str,
    goal: str,
    rho_pred: float,
    sqi_pred: float,
    rho_actual: float,
    sqi_actual: float,
    rho_err: float,
    sqi_err: float,
    confidence: float,
    thresholds: Dict[str, Any],
    cause: str = "prediction_miss",
) -> None:
    rec = {
        "ts": float(ts),
        "session": str(session),
        "goal": str(goal),
        "rho_pred": float(rho_pred),
        "sqi_pred": float(sqi_pred),
        "rho_actual": float(rho_actual),
        "sqi_actual": float(sqi_actual),
        "rho_err": float(rho_err),
        "sqi_err": float(sqi_err),
        "confidence": float(confidence),
        "thresholds": dict(thresholds or {}),
        "cause": str(cause),
        "schema": SCHEMA,
    }

    PRED_MISS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PRED_MISS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")