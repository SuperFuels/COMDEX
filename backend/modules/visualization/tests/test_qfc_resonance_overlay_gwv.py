import os
import json
import asyncio
import tempfile
import pytest

from backend.modules.visualization.qfc_resonance_overlay import QFCResonanceOverlay
from backend.modules.visualization.ghx_visual_bridge import GHXVisualBridge
from backend.modules.photon.resonance.resonance_ledger import ResonanceLedger


class DummyGHX(GHXVisualBridge):
    """Minimal GHX stub returning deterministic frames."""
    def __init__(self):
        # supply dummy ledger required by base class
        super().__init__(ledger=ResonanceLedger())

    async def build_frame(self):
        return {
            "stability": 0.92,
            "nodes": [
                {"id": "n1", "color": "hsl(120,80%,80%)"},
                {"id": "n2", "color": "hsl(240,80%,80%)"},
            ],
            "edges": [
                {"source": "n1", "target": "n2", "coherence": 0.87, "phi": 0.15},
            ],
        }


@pytest.mark.asyncio
async def test_overlay_and_gwv_recording(monkeypatch):
    """Ensure QFCResonanceOverlay broadcasts and logs to .gwv correctly."""
    ghx = DummyGHX()
    overlay = QFCResonanceOverlay(ghx)

    # Patch broadcast_qfc_update to simulate success
    async def mock_broadcast_qfc_update(container_id, overlay_data):
        return {"ok": True, "container": container_id, "node_count": len(overlay_data["nodes"])}

    monkeypatch.setattr(
        "backend.modules.visualization.qfc_resonance_overlay.broadcast_qfc_update",
        mock_broadcast_qfc_update,
    )

    # Use temp directory for output
    tmpdir = tempfile.mkdtemp()
    real_join = os.path.join  # keep original safe reference

    def local_join(*args):
        """Intercept gwv_writer joins; preserve system behavior elsewhere."""
        # If gwv_writer tries to save in snapshots/gwv, redirect to tmpdir
        if args and "snapshots/gwv" in str(args[0]):
            filename = os.path.basename(args[-1])
            return real_join(tmpdir, filename)
        return real_join(*args)

    # Patch only gwv_writer’s join and makedirs (not global os.path)
    monkeypatch.setattr(
        "backend.modules.glyphwave.gwv_writer.os.makedirs", lambda d, exist_ok=True: None
    )
    monkeypatch.setattr(
        "backend.modules.glyphwave.gwv_writer.os.path.join", local_join
    )

    # Run overlay broadcast
    result = await overlay.broadcast_overlay("test.overlay.dc")
    assert result["status"] == "broadcast"
    assert result["nodes"] == 2

    # Validate .gwv file written
    gwv_files = [f for f in os.listdir(tmpdir) if f.endswith(".gwv")]
    assert gwv_files, "No .gwv file written"

    gwv_path = os.path.join(tmpdir, gwv_files[0])
    with open(gwv_path) as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert "collapse_rate" in data[0]
    assert "decoherence_rate" in data[0]
    assert 0 <= data[0]["collapse_rate"] <= 1.0
    assert 0 <= data[0]["decoherence_rate"] <= 1.0