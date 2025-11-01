# -*- coding: utf-8 -*-
"""
Mock GWV Session Generator - Tessaris / CFE v0.3.x
Generates synthetic .gwv holographic visualization data
for testing GHX/QFC replay and overlay alignment.
"""

import json, os, time, random

def generate_mock_gwv(
    out_path="/workspaces/COMDEX/backend/telemetry/last_session.gwv",
    frames=120,
):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    session = {
        "version": "1.1",
        "meta": {
            "generator": "Tessaris Mock Session",
            "timestamp": time.time(),
            "frames": frames,
        },
        "frames": [],
    }

    for i in range(frames):
        t = time.time()
        frame = {
            "frame_id": f"frame_{i:04d}",
            "beam_id": f"beam_{i%8:02d}",
            "timestamp": t,
            "coherence": round(random.uniform(0.95, 1.0), 5),
            "phase": round(random.uniform(0, 3.14), 3),
            "power": round(random.uniform(0.8, 1.2), 3),
        }
        session["frames"].append(frame)
        time.sleep(0.002)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2)

    print(f"✅ Mock GWV session generated -> {out_path}")

if __name__ == "__main__":
    generate_mock_gwv()