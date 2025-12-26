from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

def _utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

def run_hash_from_dict(d: Mapping[str, Any]) -> str:
    payload = json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:7]

def write_run_artifacts(*, base_dir: Path, test_id: str, run_hash: str, run: Mapping[str, Any]) -> Path:
    out_dir = base_dir / test_id / run_hash
    out_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "test_id": test_id,
        "run_hash": run_hash,
        "controller": run.get("controller"),
        "timestamp_utc": _utc_now_iso(),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")

    cfg = run.get("config", {})
    (out_dir / "config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n")

    run_full = dict(run)
    run_full["run_hash"] = run_hash
    (out_dir / "run.json").write_text(json.dumps(run_full, indent=2, sort_keys=True) + "\n")

    C_series = run.get("C_series", [])
    sigma_series = run.get("sigma_series", [])
    norm_series = run.get("norm_series", [])

    rows = ["t,C,sigma,norm"]
    for i in range(min(len(C_series), len(sigma_series), len(norm_series))):
        rows.append(f"{i},{C_series[i]},{sigma_series[i]},{norm_series[i]}")
    (out_dir / "metrics.csv").write_text("\n".join(rows) + "\n")

    return out_dir
