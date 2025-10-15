import os
import json
import asyncio
import pytest
from pathlib import Path

from backend.modules.visualization.ghx_visual_bridge import GHXVisualBridge
from backend.modules.glyphwave.gwv_writer import GWVWriter
from backend.modules.photon.resonance.resonance_ledger import ResonanceLedger


class DummyLedger(ResonanceLedger):
    """Stubbed resonance ledger for replay + visualization testing."""

    def __init__(self):
        super().__init__()
        self._links = [
            ("A", "B", {"phi_delta": 0.12, "coherence": 0.88}),
            ("B", "C", {"phi_delta": 0.05, "coherence": 0.92}),
        ]

    def active_links(self):
        return self._links

    async def compute_lyapunov_stability(self) -> float:
        return 0.96

    async def snapshot(self):
        return {
            "nodes": ["A", "B", "C"],
            "edges": [("A", "B"), ("B", "C")],
            "stability": 0.96,
        }


@pytest.mark.asyncio
async def test_ghx_replay_cycle(tmp_path):
    """Verify that GHXVisualBridge can start, pause, resume, and stop replay."""

    # Step 1: Create dummy GWV file
    gwv_writer = GWVWriter(output_dir=str(tmp_path))
    gwv_writer.record_frame(
        "test_container",
        {"frame": 1, "energy": 0.88},
        collapse_rate=0.02,
        decoherence_rate=0.04,
    )
    gwv_path = gwv_writer.flush_to_disk("test_container")
    assert Path(gwv_path).exists()

    # Step 2: Initialize GHX bridge with dummy ledger
    ledger = DummyLedger()
    bridge = GHXVisualBridge(ledger)

    # Step 3: Start replay
    start_result = await bridge.start_replay(gwv_path, delay=0.05)
    assert start_result["status"] == "started"

    # Allow some replay frames to process
    await asyncio.sleep(0.2)
    assert bridge._last_ingested_frame is not None

    # Step 4: Pause + Resume + Stop control
    assert bridge.pause_replay()["status"] == "paused"
    assert bridge.resume_replay()["status"] == "resumed"
    assert bridge.stop_replay()["status"] == "stopped"

    # Ensure cleanup worked
    assert bridge._replay_controller is None
    assert isinstance(bridge._last_ingested_frame, dict)