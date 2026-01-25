#!/usr/bin/env python3
"""
Aggregate Phase 3–6 demo proof into one file.

Writes:
  $DATA_ROOT/telemetry/demo_summary.json        (full JSON, human-readable)
  $DATA_ROOT/telemetry/demo_summary.lock.json   (stable JSON for sha256 locks)

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
from typing import Any, Dict, List, Optional


def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_jsonl(path: Path, limit: int = 200_000) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= limit:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass
    return out


def _avg(nums: List[float]) -> Optional[float]:
    if not nums:
        return None
    return float(sum(nums) / len(nums))


def _env_thresholds() -> Dict[str, Any]:
    # mirror your Phase 5 env gates (record what was used)
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


def _write_pretty(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_canonical(path: Path, obj: Any) -> None:
    # canonical encoding for hashing (stable ordering + no pretty whitespace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _make_lock(full: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce a stable lock representation.
    Goal: deterministic across runs, even if underlying counts drift.
    Keep only:
      - thresholds (env + rollup) as recorded
      - set of deny reason keys (not counts)
      - artifact presence booleans (not paths)
    """
    deny_reasons = full.get("deny_reasons") if isinstance(full.get("deny_reasons"), dict) else {}
    thresholds = full.get("thresholds") if isinstance(full.get("thresholds"), dict) else {}

    # Stable: list of deny reason keys only (no counts)
    deny_reason_keys = sorted([k for k in deny_reasons.keys() if isinstance(k, str) and k])

    # Stable: artifact presence (bool), not paths
    art = full.get("artifacts") if isinstance(full.get("artifacts"), dict) else {}
    artifacts_present: Dict[str, bool] = {k: bool(art.get(k)) for k in sorted(art.keys())}

    lock = {
        "schema": "AION.DemoSummaryLock.v3",
        "thresholds": {
            "env": thresholds.get("env"),
            "rollup": thresholds.get("rollup"),
        },
        "deny_reason_keys": deny_reason_keys,
        "artifacts_present": artifacts_present,
    }
    return lock


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

    # load
    turn = _read_jsonl(turn_log_p) if turn_log_p.exists() else []
    corr = _read_jsonl(corr_p) if corr_p.exists() else []
    fc = _read_jsonl(forecast_jsonl_p) if forecast_jsonl_p.exists() else []
    miss = _read_jsonl(miss_p) if miss_p.exists() else []
    risk = _read_jsonl(risk_p) if risk_p.exists() else []
    goals = _read_jsonl(goal_p) if goal_p.exists() else []

    rollup = _read_json(rollup_p) if rollup_p.exists() else None
    playback = _read_json(playback_p) if playback_p.exists() else None

    # session id (best-effort)
    session_id = None
    if isinstance(rollup, dict) and rollup.get("session"):
        session_id = rollup.get("session")
    elif isinstance(playback, dict) and playback.get("session"):
        session_id = playback.get("session")

    # denies / ADR / misc from turn log
    n_turns = len(turn)
    denies = 0
    adr_active_turns = 0
    deny_reasons: Dict[str, int] = {}
    for r in turn:
        allow = r.get("allow_learn")
        if allow is False:
            denies += 1
        if r.get("adr_active") is True:
            adr_active_turns += 1
        dr = r.get("deny_reason")
        if isinstance(dr, str) and dr:
            deny_reasons[dr] = deny_reasons.get(dr, 0) + 1

    # averages (human view only; DO NOT put these in lock)
    def _to_f(x: Any) -> Optional[float]:
        try:
            if isinstance(x, (int, float)):
                return float(x)
            if isinstance(x, str) and x.strip():
                return float(x)
        except Exception:
            return None
        return None

    avg_conf = _avg([v for v in (_to_f(r.get("confidence")) for r in fc) if v is not None])
    avg_rho_err = _avg([v for v in (_to_f(r.get("rho_err")) for r in miss) if v is not None])
    avg_sqi_err = _avg([v for v in (_to_f(r.get("sqi_err")) for r in miss) if v is not None])

    full = {
        "schema": "AION.DemoSummary.v1",
        "ts": time.time(),
        "data_root": str(root),
        "session": session_id,
        "counts": {
            "n_turns": n_turns,
            "n_denies": denies,
            "n_adr_active_turns": adr_active_turns,
            "n_corrections": len(corr),
            "n_forecasts": len(fc),
            "n_prediction_miss": len(miss),
            "n_risk_awareness": len(risk),
            "n_goal_transitions": len(goals),
        },
        "averages": {
            "avg_confidence": avg_conf,
            "avg_rho_err": avg_rho_err,
            "avg_sqi_err": avg_sqi_err,
        },
        "deny_reasons": deny_reasons,
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

    out_json = tel / "demo_summary.json"
    out_lock = tel / "demo_summary.lock.json"

    _write_pretty(out_json, full)
    _write_canonical(out_lock, _make_lock(full))

    # print the lock path (keeps your step logs clean & greppable)
    print(str(out_lock))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())