# -*- coding: utf-8 -*-
"""
Mock GWV Session Generator — Tessaris / UltraQFC Integration Test

Purpose:
    • Generate a synthetic holographic wave session (.gwv)
    • Each frame simulates beam coherence + phase data
    • Enables GHX/QFC overlay validation & replay testing

Usage:
    PYTHONPATH=. python backend/tests/util/mock_gwv_session.py
Output:
    backend/telemetry/last_session.gwv
"""

import json
import os
import time
import random
from datetime import datetime

# Output path
OUT_PATH = "/workspaces/COMDEX/backend/telemetry/last_session.gwv"
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

# Synthetic GWV session
session = {
    "session_id": f"mock_gwv_{datetime.utcnow().isoformat()}Z",
    "source": "MockGenerator_v0.3.2",
    "frames": []
}

# Generate 10 synthetic frames
for i in range(10):
    frame = {
        "frame_id": f"frame_{i:03}",
        "beam_id": f"beam_{i % 3}",
        "timestamp": time.time() + i * 0.05,
        "coherence": round(random.uniform(0.80, 0.99), 3),
        "phase_shift": round(random.uniform(-3.14, 3.14), 4),
        "intensity": round(random.uniform(0.7, 1.0), 3),
        "meta": {"tier": i % 5, "holo": True}
    }
    session["frames"].append(frame)

# Write session file
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(session, f, indent=2)

print(f"✅ Mock GWV session created → {OUT_PATH}")
print(f"📊 Frames: {len(session['frames'])}, coherence≈{session['frames'][0]['coherence']}")