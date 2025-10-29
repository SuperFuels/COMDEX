# ============================================================
# 🔁 Photon Timeline Replay Engine
# ============================================================

import os
import json
import asyncio
from typing import List, Dict, Any

from datetime import datetime
from backend.modules.visualization.qfc_ws_broadcaster import broadcast_qfc_update

TELEMETRY_DIR = "artifacts/telemetry"


def list_available_snapshots(limit: int = 10) -> List[str]:
    """Return the N most recent .ptn telemetry files."""
    if not os.path.exists(TELEMETRY_DIR):
        return []
    files = [
        f for f in os.listdir(TELEMETRY_DIR)
        if f.endswith(".ptn")
    ]
    files.sort(reverse=True)
    return files[:limit]


async def replay_timeline(limit: int = 5, broadcast: bool = True, delay: float = 0.8) -> List[Dict[str, Any]]:
    """
    Replay telemetry files sequentially.
    Each file represents one Photon resonance event.
    """
    if not os.path.exists(TELEMETRY_DIR):
        raise FileNotFoundError("No telemetry directory found at artifacts/telemetry")

    snapshots = list_available_snapshots(limit)
    if not snapshots:
        raise FileNotFoundError("No .ptn telemetry files found")

    frames: List[Dict[str, Any]] = []

    for filename in snapshots:
        path = os.path.join(TELEMETRY_DIR, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load telemetry file {filename}: {e}")
            continue

        frame = {
            "file": filename,
            "timestamp": data.get("timestamp"),
            "state": data.get("state", {}),
            "sqi": data.get("sqi_feedback", {}),
            "qqc": data.get("qqc_feedback", {}),
        }
        frames.append(frame)

        if broadcast:
            await broadcast_qfc_update({
                "type": "qfc_timeline_frame",
                "source": "photon_replay",
                "payload": frame,
            })
            print(f"🚀 Broadcasted replay frame from {filename}")

        if delay > 0:
            await asyncio.sleep(delay)

    print(f"✅ Completed replay of {len(frames)} Photon frames")
    return frames