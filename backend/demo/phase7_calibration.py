#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


def _read_jsonl(path: Path, limit: int = 500_000) -> List[Dict[str, Any]]:
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
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        out.append(obj)
                except Exception:
                    continue
    except Exception:
        pass
    return out


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _write_json(path: Path, obj: Any) -> None:
    # canonical stable encoding for hashing
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, s: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(s, encoding="utf-8")


def _to_f(x: Any) -> Optional[float]:
    try:
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str) and x.strip():
            return float(x)
    except Exception:
        return None
    return None


def _get_thresholds_from_rollup(rollup: Optional[Dict[str, Any]]) -> Tuple[float, float, float]:
    # Fallbacks mirror Phase 6 env defaults (but rollup is preferred)
    min_conf = 0.6
    rho_err = 0.25
    sqi_err = 0.25

    if isinstance(rollup, dict):
        th = rollup.get("thresholds")
        if isinstance(th, dict):
            min_conf = _to_f(th.get("forecast_min_conf")) or min_conf
            rho_err = _to_f(th.get("forecast_rho_err")) or rho_err
            sqi_err = _to_f(th.get("forecast_sqi_err")) or sqi_err

    # Env can override (and Phase 6 sets these)
    min_conf = _to_f(os.getenv("AION_FORECAST_MIN_CONF")) or min_conf
    rho_err = _to_f(os.getenv("AION_FORECAST_RHO_ERR")) or rho_err
    sqi_err = _to_f(os.getenv("AION_FORECAST_SQI_ERR")) or sqi_err
    return float(min_conf), float(rho_err), float(sqi_err)


def _bin_index(conf: float) -> int:
    # 10 bins: [0.0-0.1), ... [0.9-1.0], with 1.0 clamped to last bin
    if conf >= 1.0:
        return 9
    if conf <= 0.0:
        return 0
    i = int(conf * 10.0)
    if i < 0:
        i = 0
    if i > 9:
        i = 9
    return i


def _export_reliability_csv_and_md(tel: Path) -> None:
    curve_p = tel / "reliability_curve.json"
    metrics_p = tel / "calibration_metrics.json"
    if not curve_p.exists() or not metrics_p.exists():
        return

    curve = json.loads(curve_p.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_p.read_text(encoding="utf-8"))

    bins = curve.get("bins") or []
    n_samples = int(curve.get("n_samples") or 0)
    ece = float(metrics.get("ece") or 0.0)

    # worst bin gap among bins with n>0 (stable tie-break: higher bin index wins)
    worst_gap = 0.0
    worst_bin: Optional[int] = None
    for b in bins:
        n = int(b.get("n") or 0)
        if n <= 0:
            continue
        conf = b.get("avg_conf")
        acc = b.get("emp_acc")
        if conf is None or acc is None:
            continue
        gap = abs(float(acc) - float(conf))
        bi = int(b.get("bin") or 0)
        if (gap > worst_gap) or (gap == worst_gap and (worst_bin is None or bi > worst_bin)):
            worst_gap = float(gap)
            worst_bin = bi

    # CSV: always 10 rows, chart-friendly
    csv_p = tel / "reliability_curve.csv"
    lines = ["bin,lo,hi,n,avg_conf,emp_acc,gap"]
    by_bin: Dict[int, Dict[str, Any]] = {int(b.get("bin", -1)): b for b in bins if isinstance(b, dict)}
    for i in range(10):
        lo = i / 10.0
        hi = (i + 1) / 10.0
        b = by_bin.get(i, {"bin": i, "n": 0, "avg_conf": None, "emp_acc": None})
        n = int(b.get("n") or 0)
        conf = b.get("avg_conf")
        acc = b.get("emp_acc")
        if n > 0 and conf is not None and acc is not None:
            conf_f = float(conf)
            acc_f = float(acc)
            gap = abs(acc_f - conf_f)
            lines.append(f"{i},{lo:.6f},{hi:.6f},{n},{conf_f:.6f},{acc_f:.6f},{gap:.6f}")
        else:
            # keep blanks for missing values to be spreadsheet-friendly
            lines.append(f"{i},{lo:.6f},{hi:.6f},{n},,,0.000000")
    _write_text(csv_p, "\n".join(lines) + "\n")

    # Optional MD summary
    md_p = tel / "reliability_curve.md"
    worst_str = "(none)" if worst_bin is None else f"bin {worst_bin} (gap={worst_gap:.6f})"
    md = (
        "# Phase 7.1 — Reliability Curve Summary\n\n"
        f"- n_samples: {n_samples}\n"
        f"- ECE: {ece:.6f}\n"
        f"- worst_bin_gap: {worst_str}\n"
        "\n"
        "Files:\n"
        "- telemetry/reliability_curve.json\n"
        "- telemetry/reliability_curve.csv\n"
        "- telemetry/calibration_metrics.json\n"
    )
    _write_text(md_p, md)


def main() -> int:
    root = _data_root()
    tel = root / "telemetry"

    miss_jsonl = tel / "prediction_miss_log.jsonl"
    rollup_json = tel / "forecast_report.json"

    if not miss_jsonl.exists():
        raise SystemExit("Missing telemetry/prediction_miss_log.jsonl (run Phase 6 first)")

    miss = _read_jsonl(miss_jsonl)
    rollup = _read_json(rollup_json) if rollup_json.exists() else None

    min_conf, rho_th, sqi_th = _get_thresholds_from_rollup(rollup)

    # Calibrate on miss events (they carry realized errors)
    events: List[Dict[str, Any]] = []
    for r in miss:
        conf = _to_f(r.get("confidence"))
        rho_err = _to_f(r.get("rho_err"))
        sqi_err = _to_f(r.get("sqi_err"))
        if conf is None:
            conf = _to_f(r.get("conf")) or _to_f(r.get("p"))
        if conf is None or rho_err is None or sqi_err is None:
            continue

        within = (conf >= min_conf) and (rho_err <= rho_th) and (sqi_err <= sqi_th)
        bi = _bin_index(conf)
        events.append(
            {
                "schema": "AION.ForecastCalibration.v1",
                "confidence": float(conf),
                "rho_err": float(rho_err),
                "sqi_err": float(sqi_err),
                "within_threshold": bool(within),
                "bin": int(bi),
            }
        )

    # Deterministic ordering for the derived log (stable across runs given same inputs)
    events.sort(
        key=lambda e: (
            int(e["bin"]),
            float(e["confidence"]),
            float(e["rho_err"]),
            float(e["sqi_err"]),
            1 if e["within_threshold"] else 0,
        )
    )

    # Derived event log (optional but useful)
    cal_log_p = tel / "forecast_calibration.jsonl"
    cal_log_p.parent.mkdir(parents=True, exist_ok=True)
    with open(cal_log_p, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")

    # Build 10-bin reliability curve
    bins: List[Dict[str, Any]] = []
    n_samples = len(events)

    for i in range(10):
        xs = [e for e in events if int(e["bin"]) == i]
        n = len(xs)
        if n == 0:
            bins.append({"bin": i, "n": 0, "avg_conf": None, "emp_acc": None})
            continue
        avg_conf = sum(float(e["confidence"]) for e in xs) / n
        emp_acc = sum(1.0 for e in xs if e["within_threshold"]) / n
        bins.append({"bin": i, "n": n, "avg_conf": float(avg_conf), "emp_acc": float(emp_acc)})

    # ECE-style metric
    ece = 0.0
    if n_samples > 0:
        for b in bins:
            n = int(b["n"])
            if n == 0:
                continue
            w = n / n_samples
            avg_conf = b["avg_conf"]
            emp_acc = b["emp_acc"]
            if avg_conf is None or emp_acc is None:
                continue
            ece += w * abs(float(avg_conf) - float(emp_acc))
    ece = float(ece)

    curve_obj = {
        "schema": "AION.ReliabilityCurve.v1",
        "n_bins": 10,
        "n_samples": int(n_samples),
        "bins": bins,
        "thresholds": {
            "forecast_min_conf": float(min_conf),
            "forecast_rho_err": float(rho_th),
            "forecast_sqi_err": float(sqi_th),
        },
    }
    metrics_obj = {
        "schema": "AION.CalibrationMetrics.v1",
        "n_bins": 10,
        "n_samples": int(n_samples),
        "ece": ece,
    }

    _write_json(tel / "reliability_curve.json", curve_obj)
    _write_json(tel / "calibration_metrics.json", metrics_obj)

    # Phase 7.1 exports
    _export_reliability_csv_and_md(tel)

    # minimal + greppable
    print(str(tel / "reliability_curve.json"))
    print(str(tel / "calibration_metrics.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())