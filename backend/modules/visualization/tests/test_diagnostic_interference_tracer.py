import os
import json
import tempfile
import pytest
import asyncio

from backend.modules.visualization.diagnostic_interference_tracer import DiagnosticInterferenceTracer
from backend.modules.visualization.ghx_visual_bridge import GHXVisualBridge
from backend.cfe.cfe_feedback_loop import CFEFeedbackLoop


class DummyGHX(GHXVisualBridge):
    """Mock GHX bridge for deterministic diagnostic testing."""
    def __init__(self):
        super().__init__(ledger=None)

    async def build_frame(self):
        # Simulated GHX frame with varied phase and coherence
        return {
            "stability": 0.88,
            "nodes": [
                {"id": "a", "color": "hsl(120,80%,70%)"},
                {"id": "b", "color": "hsl(240,80%,70%)"},
            ],
            "edges": [
                {"source": "a", "target": "b", "phi": 0.0, "coherence": 1.0},   # strong constructive
                {"source": "b", "target": "a", "phi": 0.5, "coherence": 0.9},   # near destructive
                {"source": "a", "target": "a", "phi": 0.25, "coherence": 0.6},  # neutral
            ],
        }


class DummyFeedback(CFEFeedbackLoop):
    """Mock CFE feedback providing static resonance metrics."""
    def __init__(self):
        self.last_feedback = {
            "resonance_gain": 0.95,
            "symbolic_temperature": 0.2,
            "reasoning_depth": 5,
        }


@pytest.mark.asyncio
async def test_build_diagnostic_frame(tmp_path, monkeypatch):
    """Ensure interference zones are correctly classified and saved."""
    ghx = DummyGHX()
    feedback = DummyFeedback()
    tracer = DiagnosticInterferenceTracer(ghx, feedback)

    # Patch GWV export to temp folder
    out_dir = tmp_path / "gwv"
    out_dir.mkdir()
    import os

    # Capture the real os.path.join before patching
    _real_join = os.path.join

    monkeypatch.setattr("backend.modules.glyphwave.gwv_writer.os.makedirs", lambda *a, **kw: None)
    monkeypatch.setattr(
        "backend.modules.glyphwave.gwv_writer.os.path.join",
        lambda *parts: str(_real_join(str(out_dir), *parts[1:])),
    )

    frame = await tracer.build_diagnostic_frame()
    assert "zones" in frame
    assert frame["constructive_count"] >= 1
    assert frame["destructive_count"] >= 1
    assert frame["stability"] == pytest.approx(0.88, rel=1e-2)

    # Check a sample interference index range
    for zone in frame["zones"]:
        assert -1.0 <= zone["interference_index"] <= 1.0

    # Validate .gwv export path
    path = tracer._ring_buffer.export_to_gwv("diag_test", str(out_dir))
    print(f"\n[DEBUG] GWV export path: {path}")
    if os.path.exists(path):
        with open(path, "r") as f:
            raw = f.read()
            print("\n[DEBUG] --- GWV FILE CONTENT ---")
            print(raw[:2000])  # print first ~2KB
            print("[DEBUG] --- END ---\n")
    else:
        print("[DEBUG] GWV FILE MISSING!")

    # Then run assertions as usual
    data = json.loads(raw)
    assert os.path.exists(path)
    data = json.load(open(path))
    assert "frames" in data
    assert isinstance(data["frames"], list)
    assert any("interference_index" in f["frame"] for f in data["frames"])


@pytest.mark.asyncio
async def test_broadcast_diagnostics(monkeypatch):
    """Simulate WebSocket broadcast of diagnostic frame."""
    ghx = DummyGHX()
    feedback = DummyFeedback()
    tracer = DiagnosticInterferenceTracer(ghx, feedback)

    async def mock_broadcast(container_id, frame):
        return {"ok": True, "zones": len(frame["zones"])}

    monkeypatch.setattr(
        "backend.modules.visualization.diagnostic_interference_tracer.broadcast_qfc_update",
        mock_broadcast,
    )

    result = await tracer.broadcast_diagnostics("diag.container")
    assert result["status"] == "broadcast"
    assert "zones" in result