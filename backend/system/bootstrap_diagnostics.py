#!/usr/bin/env python3
"""
Tessaris Bootstrap Diagnostics
──────────────────────────────────────────────
Scans Aion subsystem state files and checkpoints,
then emits a unified system bootstrap map:
    data/system/bootstrap_map.json
"""

import json, os, time
from pathlib import Path

DATA_DIR = Path("data")
SYSTEM_DIR = DATA_DIR / "system"
SYSTEM_DIR.mkdir(parents=True, exist_ok=True)
MAP_PATH = SYSTEM_DIR / "bootstrap_map.json"

MODULES = {
    "PAL": "backend/modules/aion_perception/checkpoints/pal_state_SQI_Stabilized_v2.json",
    "PredictiveBias": "data/predictive/predictive_bias_state.json",
    "QWave": "data/sqi_checkpoint_equilibrium_lock_*.json",
    "Snapshot": "data/analysis/pal_snapshots.jsonl",
}

def get_status(path):
    import glob
    files = glob.glob(path) if "*" in path else [path]
    if not files:
        return {"status": "missing"}
    latest = max(files, key=os.path.getmtime)
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(latest)))
    size = os.path.getsize(latest)
    return {"status": "ok", "path": latest, "timestamp": ts, "size": size}

def build_bootstrap_map():
    report = {name: get_status(p) for name, p in MODULES.items()}
    report["resonance_sync"] = "ok" if all(r.get("status") == "ok" for r in report.values()) else "desync"
    with open(MAP_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"💾 Bootstrap map saved -> {MAP_PATH}")
    return report

if __name__ == "__main__":
    print("🧩 Running Tessaris bootstrap diagnostics...")
    report = build_bootstrap_map()
    print(json.dumps(report, indent=2))