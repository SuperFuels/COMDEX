# -*- coding: utf-8 -*-
"""
Mock Telemetry Generator - Tessaris / CFE v0.3.x
Generates synthetic telemetry logs aligned with last_session.gwv
so that GHX/QFC overlay validation can compute coherence/time deltas.

Outputs:
    /workspaces/COMDEX/backend/telemetry/logs/mock_telem.json
"""

import os
import json
import random
import time
from datetime import datetime

GWV_PATH = "/workspaces/COMDEX/backend/telemetry/last_session.gwv"
OUT_PATH = "/workspaces/COMDEX/backend/telemetry/logs/mock_telem.json"

def generate_mock_telemetry(gwv_path: str, out_path: str):
    if not os.path.exists(gwv_path):
        print(f"⚠️ No GWV session found at {gwv_path}")
        return

    # Ensure logs directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(gwv_path, "r", encoding="utf-8") as f:
        gwv = json.load(f)

    telem_entries = []
    for frame in gwv.get("frames", []):
        beam_id = frame["beam_id"]
        # introduce small random drift to simulate measurement variance
        drift_t = random.uniform(-0.002, 0.002)
        drift_c = random.uniform(-0.01, 0.01)
        telem_entries.append({
            "beam_id": beam_id,
            "timestamp": frame["timestamp"] + drift_t,
            "coherence": frame["coherence"] + drift_c,
            "intensity": frame["intensity"],
            "recorded_at": datetime.utcnow().isoformat() + "Z"
        })

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(telem_entries, f, indent=2)

    print(f"✅ Mock telemetry generated -> {out_path}")
    print(f"📈 Entries: {len(telem_entries)}, Δt≈±2 ms, Δcoherence≈±0.01")


if __name__ == "__main__":
    generate_mock_telemetry(GWV_PATH, OUT_PATH)