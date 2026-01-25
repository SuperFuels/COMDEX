#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))

def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def _write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")

def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def _sha256_file(p: Path) -> str:
    return _sha256_bytes(p.read_bytes())

def _sanitize_forecast_report(obj: Dict[str, Any]) -> Dict[str, Any]:
    # forecast_report.json (rollup)
    out = dict(obj)
    # volatile keys
    out.pop("ts", None)
    out.pop("timestamp", None)
    out.pop("session", None)
    return out

def _sanitize_demo_summary(obj: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(obj)
    # volatile keys
    out.pop("ts", None)
    out.pop("session", None)
    out.pop("data_root", None)

    # scrub absolute artifact paths if present
    artifacts = out.get("artifacts")
    if isinstance(artifacts, dict):
        new_art = {}
        for k, v in artifacts.items():
            if isinstance(v, str):
                # keep only the tail-ish relative hint (stable)
                new_art[k] = re.sub(r"^.*?/telemetry/", "telemetry/", v)
                new_art[k] = re.sub(r"^.*?/sessions/", "sessions/", new_art[k])
                new_art[k] = re.sub(r"^.*?/memory/", "memory/", new_art[k])
            else:
                new_art[k] = v
        out["artifacts"] = new_art

    return out

def main() -> int:
    root = _data_root()
    tel = root / "telemetry"

    forecast_p = tel / "forecast_report.json"
    demo_sum_p = tel / "demo_summary.json"

    forecast = _read_json(forecast_p) or {}
    demo_sum = _read_json(demo_sum_p) or {}

    forecast_lock = _sanitize_forecast_report(forecast) if isinstance(forecast, dict) else {}
    demo_sum_lock = _sanitize_demo_summary(demo_sum) if isinstance(demo_sum, dict) else {}

    out_forecast = tel / "forecast_report.lock.json"
    out_demo = tel / "demo_summary.lock.json"
    _write_json(out_forecast, forecast_lock)
    _write_json(out_demo, demo_sum_lock)

    # bundle sha256
    bundle = {
        "schema": "AION.Phase6LockBundle.v1",
        "files": {
            "telemetry/forecast_report.lock.json": _sha256_file(out_forecast),
            "telemetry/demo_summary.lock.json": _sha256_file(out_demo),
        },
    }
    bundle_p = tel / "phase6_lock_bundle.json"
    _write_json(bundle_p, bundle)

    print(str(out_forecast))
    print(str(out_demo))
    print(str(bundle_p))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())