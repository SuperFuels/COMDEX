#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


def _read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    out: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            out.append(json.loads(s))
        except Exception:
            continue
    return out


def _safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _avg(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    return sum(vals) / float(len(vals))


def _thresholds_from_env() -> dict:
    # Prediction miss thresholds
    min_conf = float(os.getenv("AION_FORECAST_MIN_CONF", "0.6") or "0.6")
    rho_err = float(os.getenv("AION_FORECAST_RHO_ERR", "0.15") or "0.15")
    sqi_err = float(os.getenv("AION_FORECAST_SQI_ERR", "0.15") or "0.15")

    # Risk thresholds
    risk_min_conf = float(os.getenv("AION_RISK_MIN_CONF", "0.6") or "0.6")
    risk_min_score = float(os.getenv("AION_RISK_MIN_SCORE", "0.65") or "0.65")

    return {
        "forecast_min_conf": min_conf,
        "forecast_rho_err": rho_err,
        "forecast_sqi_err": sqi_err,
        "risk_min_conf": risk_min_conf,
        "risk_min_score": risk_min_score,
    }


def write_forecast_report_summary(session: str, ts: Optional[float] = None) -> dict:
    """
    Reads:
      telemetry/forecast_report.jsonl (AION.Forecast.v1)
      telemetry/prediction_miss_log.jsonl (AION.PredictionMiss.v1)
      telemetry/risk_awareness_log.jsonl (AION.RiskAwareness.v1)

    Writes:
      telemetry/forecast_report.json (AION.ForecastReport.v1)
    """
    ts = float(ts if ts is not None else time.time())
    root = _data_root()
    telem = root / "telemetry"

    forecast_path = telem / "forecast_report.jsonl"
    miss_path = telem / "prediction_miss_log.jsonl"
    risk_path = telem / "risk_awareness_log.jsonl"
    out_path = telem / "forecast_report.json"

    forecasts = _read_jsonl(forecast_path)
    misses = _read_jsonl(miss_path)
    risks = _read_jsonl(risk_path)

    # Filter by session (strict)
    forecasts_s = [r for r in forecasts if r.get("session") == session]
    misses_s = [r for r in misses if r.get("session") == session]
    risks_s = [r for r in risks if r.get("session") == session]

    confs: List[float] = []
    for r in forecasts_s:
        v = _safe_float(r.get("confidence"))
        if v is not None:
            confs.append(v)

    rho_errs: List[float] = []
    sqi_errs: List[float] = []
    for r in misses_s:
        v1 = _safe_float(r.get("rho_err"))
        v2 = _safe_float(r.get("sqi_err"))
        if v1 is not None:
            rho_errs.append(v1)
        if v2 is not None:
            sqi_errs.append(v2)

    report = {
        "schema": "AION.ForecastReport.v1",
        "ts": ts,
        "session": session,
        "n_forecasts": len(forecasts_s),
        "n_prediction_miss": len(misses_s),
        "n_risk_awareness": len(risks_s),
        "avg_confidence": _avg(confs),
        "avg_rho_err": _avg(rho_errs) if rho_errs else None,
        "avg_sqi_err": _avg(sqi_errs) if sqi_errs else None,
        "thresholds": _thresholds_from_env(),
    }

    telem.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report