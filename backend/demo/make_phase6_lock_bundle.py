#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
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


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _sanitize_forecast_report(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stable lock for forecast_report.json.

    DO NOT lock:
      - session, ts, timestamp
      - counts (n_forecasts, n_misses, etc.)
      - aggregates/averages/metrics that can drift

    Only lock:
      - thresholds (the gate config)
      - schema marker for traceability
    """
    o = obj or {}
    thresholds = o.get("thresholds") if isinstance(o, dict) else None

    return {
        "schema": "AION.ForecastReportLock.v2",
        "thresholds": thresholds,
    }


def _sanitize_demo_summary(obj: Dict[str, Any]) -> Dict[str, Any]:
    # If already a lock summary, keep verbatim (it is the stable artifact we hash)
    if (obj or {}).get("schema") in ("AION.DemoSummaryLock.v2", "AION.DemoSummaryLock.v3"):
        return obj

    out = dict(obj or {})
    # volatile keys
    out.pop("ts", None)
    out.pop("session", None)
    out.pop("data_root", None)

    # scrub absolute artifact paths if present
    artifacts = out.get("artifacts")
    if isinstance(artifacts, dict):
        new_art: Dict[str, Any] = {}
        for k, v in artifacts.items():
            if isinstance(v, str):
                s = v
                s = re.sub(r"^.*?/telemetry/", "telemetry/", s)
                s = re.sub(r"^.*?/sessions/", "sessions/", s)
                s = re.sub(r"^.*?/memory/", "memory/", s)
                new_art[k] = s
            else:
                new_art[k] = v
        out["artifacts"] = new_art

    return out


def _require_exists(p: Path, msg: str) -> None:
    if not p.exists():
        raise SystemExit(msg)


def main() -> int:
    root = _data_root()
    tel = root / "telemetry"

    # Phase 6 inputs
    forecast_p = tel / "forecast_report.json"
    _require_exists(forecast_p, "Missing telemetry/forecast_report.json (run Phase 6 demo first)")

    # Prefer deterministic lock summary if present
    demo_sum_p = tel / "demo_summary.lock.json"
    if not demo_sum_p.exists():
        demo_sum_p = tel / "demo_summary.json"
    _require_exists(demo_sum_p, "Missing telemetry/demo_summary(.lock).json (run demo_summary step first)")

    forecast = _read_json(forecast_p) or {}
    demo_sum = _read_json(demo_sum_p) or {}

    forecast_lock = _sanitize_forecast_report(forecast) if isinstance(forecast, dict) else {}
    demo_sum_lock = _sanitize_demo_summary(demo_sum) if isinstance(demo_sum, dict) else {}

    out_forecast = tel / "forecast_report.lock.json"
    out_demo = tel / "demo_summary.lock.json"
    _write_json(out_forecast, forecast_lock)
    _write_json(out_demo, demo_sum_lock)

    bundle = {
        "schema": "AION.Phase6LockBundle.v1",
        "files": {
            "telemetry/forecast_report.lock.json": _sha256_file(out_forecast),
            "telemetry/demo_summary.lock.json": _sha256_file(out_demo),
        },
    }

    bundle_p = tel / "phase6_lock_bundle.json"
    _write_json(bundle_p, bundle)

    # minimal + greppable
    print(str(out_forecast))
    print(str(out_demo))
    print(str(bundle_p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())