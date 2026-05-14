"""
🧪 Test Suite - GWave Replay Emitter
Covers async frame emission, file validation, and replay control behavior.
"""

import os
import json
import asyncio
import tempfile
import pytest

from backend.modules.glyphwave.emit_gwave_replay import (
    load_gwv_file,
    emit_gwave_frames,
    ReplayController,
)
from backend.modules.glyphwave.schema.validate_gwv import safe_validate_gwv


class DummyGHXBridge:
    """Simulates GHX/QFC bridge that accepts ingested frames."""
    def __init__(self):
        self.received = []

    async def ingest_frame(self, frame):
        self.received.append(frame)


@pytest.mark.asyncio
async def test_load_gwv_file_and_validation(monkeypatch):
    """Ensure .gwv file loads and validation runs."""
    tmp = tempfile.mkdtemp()
    gwv_path = os.path.join(tmp, "sample.gwv")

    gwv_content = {
        "container_id": "test.unit",
        "snapshot_count": 2,
        "stability": 0.91,
        "frames": [
            {"timestamp": "2025-10-14T22:59:12Z", "collapse_rate": 0.1, "decoherence_rate": 0.2, "frame": {"n": 1}},
            {"timestamp": "2025-10-14T22:59:13Z", "collapse_rate": 0.2, "decoherence_rate": 0.3, "frame": {"n": 2}},
        ],
    }
    with open(gwv_path, "w", encoding="utf-8") as f:
        json.dump(gwv_content, f)

    called = {"count": 0}
    monkeypatch.setattr("backend.modules.glyphwave.emit_gwave_replay.safe_validate_gwv", lambda p: called.update(count=1))

    data = await load_gwv_file(gwv_path)
    assert "frames" in data
    assert called["count"] == 1


@pytest.mark.asyncio
async def test_emit_gwave_frames_replays_sequence():
    """Verify sequential frame replay into dummy GHX bridge."""
    tmp = tempfile.mkdtemp()
    gwv_path = os.path.join(tmp, "seq.gwv")
    gwv_data = {
        "container_id": "seq.test",
        "snapshot_count": 3,
        "stability": 1.0,
        "frames": [
            {"frame": {"a": 1}},
            {"frame": {"a": 2}},
            {"frame": {"a": 3}},
        ],
    }
    with open(gwv_path, "w", encoding="utf-8") as f:
        json.dump(gwv_data, f)

    bridge = DummyGHXBridge()
    frames = []
    async for frame in emit_gwave_frames(bridge, gwv_path, delay=0.01, loop=False):
        frames.append(frame)

    assert len(frames) == 3
    assert bridge.received == frames


@pytest.mark.asyncio
async def test_replay_controller_pause_resume(monkeypatch):
    """Ensure ReplayController can pause and resume emission."""
    tmp = tempfile.mkdtemp()
    gwv_path = os.path.join(tmp, "ctrl.gwv")
    with open(gwv_path, "w", encoding="utf-8") as f:
        json.dump({
            "container_id": "ctrl",
            "snapshot_count": 1,
            "stability": 1.0,
            "frames": [{"frame": {"signal": 42}}],
        }, f)

    bridge = DummyGHXBridge()
    rc = ReplayController(bridge, gwv_path, delay=0.01)
    await rc.start()
    rc.pause()
    await asyncio.sleep(0.05)
    rc.resume()
    await asyncio.sleep(0.05)
    rc.stop()

    # After resume, at least one frame should be ingested
    assert bridge.received, "No frames emitted after resume"