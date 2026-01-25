#!/usr/bin/env python3
"""
Aggregate demo proof into two files:

Writes:
  $DATA_ROOT/telemetry/demo_summary.json        (human / full)
  $DATA_ROOT/telemetry/demo_summary.lock.json   (deterministic / for sha256)

Reads (if present):
  - telemetry/turn_log.jsonl
  - telemetry/correction_events.jsonl
  - telemetry/forecast_report.jsonl
  - telemetry/prediction_miss_log.jsonl
  - telemetry/risk_awareness_log.jsonl
  - telemetry/forecast_report.json
  - telemetry/goal_transition_log.jsonl
  - sessions/playback_log.qdata.json
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _stable_json(obj: Any) -> str:
    # deterministic serialization (hash-safe)
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _env_thresholds() -> Dict[str, Any]:
    def _f(name: str, default: str) -> float:
        try:
            return float(os.getenv(name, default) or default)
        except Exception:
            return float(default)

    return {
        "forecast": {
            "min_conf": _f("AION_FORECAST_MIN_CONF", "0.6"),
            "rho_err": _f("AION_FORECAST_RHO_ERR", "0.25"),
            "sqi_err": _f("AION_FORECAST_SQI_ERR", "0.25"),
        },
        "risk": {
            "min_conf": _f("AION_RISK_MIN_CONF", "0.6"),
            "min_score": _f("AION_RISK_MIN_SCORE", "0.65"),
        },
    }


def main() -> int:
    root = _data_root()
    tel = root / "telemetry"
    ses = root / "sessions"

    turn_log_p = tel / "turn_log.jsonl"
    corr_p = tel / "correction_events.jsonl"
    forecast_jsonl_p = tel / "forecast_report.jsonl"
    miss_p = tel / "prediction_miss_log.jsonl"
    risk_p = tel / "risk_awareness_log.jsonl"
    rollup_p = tel / "forecast_report.json"
    goal_p = tel / "goal_transition_log.jsonl"
    playback_p = ses / "playback_log.qdata.json"

    rollup = _read_json(rollup_p) if rollup_p.exists() else None
    playback = _read_json(playback_p) if playback_p.exists() else None

    # human session id (best-effort)
    session_id = None
    if isinstance(rollup, dict) and rollup.get("session"):
        session_id = rollup.get("session")
    elif isinstance(playback, dict) and playback.get("session"):
        session_id = playback.get("session")

    # -------------------------
    # HUMAN summary (may vary)
    # -------------------------
    out_human = {
        "schema": "AION.DemoSummary.v1",
        "ts": time.time(),
        "data_root": str(root),
        "session": session_id,
        "thresholds": {
            "env": _env_thresholds(),
            "rollup": (rollup.get("thresholds") if isinstance(rollup, dict) else None),
        },
        "artifacts": {
            "turn_log": str(turn_log_p) if turn_log_p.exists() else None,
            "correction_events": str(corr_p) if corr_p.exists() else None,
            "forecast_report_jsonl": str(forecast_jsonl_p) if forecast_jsonl_p.exists() else None,
            "prediction_miss_log": str(miss_p) if miss_p.exists() else None,
            "risk_awareness_log": str(risk_p) if risk_p.exists() else None,
            "forecast_rollup": str(rollup_p) if rollup_p.exists() else None,
            "goal_transition_log": str(goal_p) if goal_p.exists() else None,
            "playback_log": str(playback_p) if playback_p.exists() else None,
        },
    }

    # -------------------------
    # LOCK summary (must be stable)
    # IMPORTANT: no counts/averages/session/time/tmp paths
    # -------------------------
    out_lock = {
        "schema": "AION.DemoSummaryLock.v2",
        "thresholds": {
            "env": _env_thresholds(),
            "rollup": (rollup.get("thresholds") if isinstance(rollup, dict) else None),
        },
        "schemas_seen": {
            "forecast_rollup": (rollup.get("schema") if isinstance(rollup, dict) else None),
        },
        "files_present": {
            "telemetry/turn_log.jsonl": turn_log_p.exists(),
            "telemetry/correction_events.jsonl": corr_p.exists(),
            "telemetry/forecast_report.jsonl": forecast_jsonl_p.exists(),
            "telemetry/prediction_miss_log.jsonl": miss_p.exists(),
            "telemetry/risk_awareness_log.jsonl": risk_p.exists(),
            "telemetry/forecast_report.json": rollup_p.exists(),
            "telemetry/goal_transition_log.jsonl": goal_p.exists(),
            "sessions/playback_log.qdata.json": playback_p.exists(),
        },
    }

    tel.mkdir(parents=True, exist_ok=True)

    human_path = tel / "demo_summary.json"
    lock_path = tel / "demo_summary.lock.json"

    human_path.write_text(json.dumps(out_human, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lock_path.write_text(_stable_json(out_lock), encoding="utf-8")

    print(str(human_path))
    print(str(lock_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())