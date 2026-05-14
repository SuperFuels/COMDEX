"""
🧪 Test - QFC Resonance Overlay + CFE Feedback Integration
Verifies that live CFE feedback telemetry is merged into GHX->QFC overlay frames.
"""

import asyncio
import pytest
from backend.modules.visualization.qfc_resonance_overlay import QFCResonanceOverlay
from backend.modules.visualization.ghx_visual_bridge import GHXVisualBridge
from backend.cfe.cfe_feedback_loop import CFEFeedbackLoop


class DummyLedger:
    async def compute_lyapunov_stability(self):
        return 0.92

    def active_links(self):
        # simulate small resonance network
        return [
            ("A", "B", {"phi_delta": 0.12, "coherence": 0.85}),
            ("B", "C", {"phi_delta": 0.22, "coherence": 0.65}),
        ]


class DummyTelemetry:
    async def collect_metrics(self):
        return {
            "collapse_rate": 0.05,
            "decoherence_rate": 0.07,
            "coherence_stability": 0.92,
        }


@pytest.mark.asyncio
async def test_feedback_overlay_integration(tmp_path):
    # set up dummy CFE + GHX bridge
    ledger = DummyLedger()
    ghx = GHXVisualBridge(ledger)
    telemetry = DummyTelemetry()

    # initialize CFE feedback loop (no async run)
    feedback = CFEFeedbackLoop(codex_runtime=None, telemetry=telemetry)
    feedback.last_feedback = {
        "symbolic_temperature": 0.2,
        "resonance_gain": 0.95,
        "reasoning_depth": 5,
    }

    overlay = QFCResonanceOverlay(ghx, feedback)
    data = await overlay.build_overlay()

    # feedback must be attached to overlay
    assert "feedback" in data
    fb = data["feedback"]
    assert pytest.approx(fb["symbolic_temperature"], rel=1e-3) == 0.2

    # verify hue bias was applied (RGB values slightly shifted)
    assert isinstance(data["nodes"], list)
    assert all("rgb" in n for n in data["nodes"])
    assert all(isinstance(n["rgb"], tuple) for n in data["nodes"])

    # simulate broadcast persistence
    result = await overlay.broadcast_overlay("test.feedback.overlay")
    assert result["status"] == "broadcast"


@pytest.mark.asyncio
async def test_feedback_overlay_without_feedback():
    """Overlay should still build cleanly if no CFEFeedbackLoop is present."""
    ledger = DummyLedger()
    ghx = GHXVisualBridge(ledger)
    overlay = QFCResonanceOverlay(ghx)
    data = await overlay.build_overlay()

    assert "feedback" in data
    assert data["feedback"] == {}
    assert isinstance(data["nodes"], list)