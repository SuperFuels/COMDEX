#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _write_json(p: Path, obj: Any) -> None:
    # Deterministic serialization (hash-safe)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
def _require_exists(p: Path, msg: str) -> None:
    if not p.exists():
        raise SystemExit(msg)

def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _sanitize_reliability_curve(curve: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase7 outputs drift if Phase6 produces a different miss stream.
    So we lock only the stable *contract*:
      - thresholds (gate config)
      - n_bins
      - bin sample counts (shape evidence)
    We deliberately do NOT lock avg_conf/emp_acc floats.
    """
    bins = curve.get("bins")
    if not isinstance(bins, list):
        bins = []

    # bin_counts keyed by "0".."9"
    bin_counts: Dict[str, int] = {}
    for b in bins:
        if not isinstance(b, dict):
            continue
        try:
            bi = int(b.get("bin"))
            n = int(b.get("n") or 0)
        except Exception:
            continue
        if 0 <= bi <= 9:
            bin_counts[str(bi)] = n

    thresholds = curve.get("thresholds") if isinstance(curve.get("thresholds"), dict) else None

    return {
        "schema": "AION.ReliabilityCurveLock.v1",
        "n_bins": int(curve.get("n_bins") or 10),
        "thresholds": thresholds,
        "bin_counts": bin_counts,
    }


def _sanitize_calibration_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    ECE numeric value drifts with the underlying event stream.
    Lock only the stable metadata.
    """
    return {
        "schema": "AION.CalibrationMetricsLock.v1",
        "n_bins": int(metrics.get("n_bins") or 10),
    }

def _sanitize_reliability_curve(obj: Dict[str, Any]) -> Dict[str, Any]:
    # Lock only stable config, NOT computed bins/counts (those can drift run-to-run)
    o = obj or {}
    th = o.get("thresholds") if isinstance(o, dict) else None
    n_bins = o.get("n_bins") if isinstance(o, dict) else None
    return {
        "schema": "AION.ReliabilityCurveLock.v1",
        "n_bins": int(n_bins) if isinstance(n_bins, (int, float, str)) and str(n_bins).strip() else 10,
        "thresholds": th,
    }


def _sanitize_calibration_metrics(obj: Dict[str, Any]) -> Dict[str, Any]:
    # Lock only stable shape, NOT computed ece / n_samples
    o = obj or {}
    n_bins = o.get("n_bins") if isinstance(o, dict) else None
    return {
        "schema": "AION.CalibrationMetricsLock.v1",
        "n_bins": int(n_bins) if isinstance(n_bins, (int, float, str)) and str(n_bins).strip() else 10,
    }

def main() -> int:
    root = _data_root()
    tel = root / "telemetry"

    rel_raw_p = tel / "reliability_curve.json"
    met_raw_p = tel / "calibration_metrics.json"

    _require_exists(rel_raw_p, "Missing telemetry/reliability_curve.json (run phase7_calibration.py first)")
    _require_exists(met_raw_p, "Missing telemetry/calibration_metrics.json (run phase7_calibration.py first)")

    rel_raw = _read_json(rel_raw_p) or {}
    met_raw = _read_json(met_raw_p) or {}

    rel_lock = _sanitize_reliability_curve(rel_raw)
    met_lock = _sanitize_calibration_metrics(met_raw)

    rel_lock_p = tel / "reliability_curve.lock.json"
    met_lock_p = tel / "calibration_metrics.lock.json"
    _write_json(rel_lock_p, rel_lock)
    _write_json(met_lock_p, met_lock)

    bundle = {
        "schema": "AION.Phase7LockBundle.v2",
        "files": {
            "telemetry/reliability_curve.lock.json": _sha256_file(rel_lock_p),
            "telemetry/calibration_metrics.lock.json": _sha256_file(met_lock_p),
        },
    }

    bundle_p = tel / "phase7_lock_bundle.json"
    _write_json(bundle_p, bundle)

    print(str(rel_lock_p))
    print(str(met_lock_p))
    print(str(bundle_p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())