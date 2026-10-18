#!/usr/bin/env python3
"""
Tessaris Bootstrap Diagnostics
──────────────────────────────────────────────
Scans Aion subsystem state files and checkpoints, then emits a content-free
availability map in the disposable external Tessaris Node state directory.
"""

import glob
import json
from pathlib import Path

from backend.modules.aion_business.runtime.content_free_diagnostics import (
    BOOTSTRAP_STATUS_SCHEMA,
    atomic_write_json,
    default_node_diagnostics_root,
    utc_now,
)

MODULES = {
    "PAL": "backend/modules/aion_perception/checkpoints/pal_state_SQI_Stabilized_v2.json",
    "PredictiveBias": "data/predictive/predictive_bias_state.json",
    "QWave": "data/sqi_checkpoint_equilibrium_lock_*.json",
    "Snapshot": "data/analysis/pal_snapshots.jsonl",
}

def get_status(path: str) -> dict[str, object]:
    files = glob.glob(path) if "*" in path else [path]
    available = any(Path(candidate).is_file() for candidate in files)
    return {"status": "available" if available else "missing"}

def build_bootstrap_map(*, output_path: str | Path | None = None):
    modules = {name: get_status(path) for name, path in MODULES.items()}
    report = {
        "schema_version": BOOTSTRAP_STATUS_SCHEMA,
        "recorded_at": utc_now(),
        "modules": modules,
        "resonance_sync": (
            "available"
            if all(item.get("status") == "available" for item in modules.values())
            else "incomplete"
        ),
        "content_free": True,
    }
    destination = Path(output_path) if output_path else (
        default_node_diagnostics_root() / "bootstrap-status.json"
    )
    atomic_write_json(destination, report)
    print(f"Bootstrap status saved -> {destination}")
    return report

if __name__ == "__main__":
    print("🧩 Running Tessaris bootstrap diagnostics...")
    report = build_bootstrap_map()
    print(json.dumps(report, indent=2))
