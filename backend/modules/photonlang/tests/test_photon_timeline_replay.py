# ============================================================
# 🧪 Photon Timeline Replay Test
# ============================================================
# Verifies .ptn snapshots can be replayed through Photon -> SQI -> QQC -> QFC.

import asyncio
import pytest
from pathlib import Path

from backend.modules.photonlang.integrations.photon_timeline_replay import (
    list_available_snapshots,
    replay_snapshot,
    replay_timeline,
)

@pytest.mark.asyncio
async def test_photon_timeline_replay_runtime():
    """Ensure that saved photon telemetry can be replayed successfully."""
    print("\n[TEST] Starting Photon Timeline Replay...")

    # 1️⃣ Verify that telemetry files exist
    snapshots = list_available_snapshots()
    assert snapshots, "No .ptn telemetry files found under artifacts/telemetry/"

    print(f"[TEST] Found {len(snapshots)} telemetry snapshots:")
    for s in snapshots:
        print(f"   - {Path(s).name}")

    # 2️⃣ Replay a single frame
    frame = await replay_snapshot(snapshots[0], broadcast=False)
    assert frame["seq"], "Replay frame missing sequence"
    assert "intensity" in frame, "Replay frame missing intensity"

    print(f"[TEST] Single-frame replay successful for {frame['seq']}")

    # 3️⃣ Replay full timeline (no QFC broadcast in test mode)
    frames = await replay_timeline(limit=3, broadcast=False, delay=0.2)
    assert isinstance(frames, list) and frames, "No frames returned from timeline replay"

    print(f"[TEST] Replayed {len(frames)} total frames.")
    print("[✅] Photon timeline replay operational.")