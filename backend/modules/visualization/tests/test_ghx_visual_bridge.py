import pytest
import asyncio
from backend.modules.visualization.ghx_visual_bridge import GHXVisualBridge
from backend.modules.photon.resonance.resonance_ledger import ResonanceLedger


@pytest.mark.asyncio
async def test_build_frame_and_color_mapping():
    ledger = ResonanceLedger()
    await ledger.register_link("a", "b", phi_delta=0.05, coherence=0.9)
    await ledger.register_link("b", "c", phi_delta=0.02, coherence=0.5)

    bridge = GHXVisualBridge(ledger)
    frame = await bridge.build_frame()

    assert "edges" in frame and len(frame["edges"]) == 2
    assert 0.0 <= frame["stability"] <= 1.0
    assert frame["type"] == "ghx_frame"
    assert all("color" in e for e in frame["edges"])


@pytest.mark.asyncio
async def test_broadcast_frame(monkeypatch):
    called = {}

    async def fake_broadcast(event):
        called["data"] = event

    monkeypatch.setattr(
        "backend.modules.visualization.ghx_visual_bridge.broadcast_event",
        fake_broadcast
    )

    ledger = ResonanceLedger()
    await ledger.register_link("x", "y", 0.01, 0.95)
    bridge = GHXVisualBridge(ledger)

    result = await bridge.broadcast_frame()
    assert result["status"] == "broadcast"
    assert "data" in called