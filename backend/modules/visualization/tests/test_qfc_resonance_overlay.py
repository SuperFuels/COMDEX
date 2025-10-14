import pytest
from backend.modules.visualization.qfc_resonance_overlay import QFCResonanceOverlay
from backend.modules.visualization.ghx_visual_bridge import GHXVisualBridge
from backend.modules.photon.resonance.resonance_ledger import ResonanceLedger


@pytest.mark.asyncio
async def test_overlay_structure_and_color_mapping():
    ledger = ResonanceLedger()
    await ledger.register_link("n1", "n2", phi_delta=0.03, coherence=0.85)
    bridge = GHXVisualBridge(ledger)
    overlay = QFCResonanceOverlay(bridge)
    frame = await overlay.build_overlay()

    assert "nodes" in frame and len(frame["nodes"]) >= 2
    assert "edges" in frame and len(frame["edges"]) >= 1
    assert frame["type"] == "qfc_resonance_overlay"
    assert all("rgb" in n for n in frame["nodes"])
    assert 0.0 <= frame["stability"] <= 1.0


@pytest.mark.asyncio
async def test_holographic_projection_and_broadcast(monkeypatch):
    called = {}

    async def fake_broadcast(cid, data):
        called["payload"] = data
        return {"status": "broadcast"}

    monkeypatch.setattr(
        "backend.modules.visualization.qfc_resonance_overlay.broadcast_qfc_update",
        fake_broadcast
    )

    ledger = ResonanceLedger()
    await ledger.register_link("a", "b", 0.02, 0.9)
    bridge = GHXVisualBridge(ledger)
    overlay = QFCResonanceOverlay(bridge)

    holo = await overlay.holographic_projection()
    assert "projection" in holo
    result = await overlay.broadcast_overlay("test.container")
    assert result["status"] == "broadcast"
    assert "payload" in called