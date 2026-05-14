# ──────────────────────────────────────────────────────────────
#  Tessaris * Test Suite: C7 Phase-State Bridge (Fixed Version)
# ──────────────────────────────────────────────────────────────

import os
import json
import pytest

# Mock CFA update method (since CFA is a singleton adapter)
class MockCFA:
    state = {}
    @classmethod
    def update_phase_state(cls, **kwargs):
        cls.state.update(kwargs)


@pytest.fixture(scope="function", autouse=True)
def patch_cfa(monkeypatch):
    """
    Replace CFA reference inside the PhaseStateBridge module
    before the class is imported or used.
    """
    import backend.modules.cognitive_fabric.cfa_phase_state_bridge as bridge_module
    monkeypatch.setattr(bridge_module, "CFA", MockCFA)
    yield
    # Cleanup after test
    MockCFA.state.clear()
    log_path = "backend/logs/phase_state_events.jsonl"
    if os.path.exists(log_path):
        os.remove(log_path)


def test_phase_state_ingestion_and_update():
    from backend.modules.cognitive_fabric.cfa_phase_state_bridge import PhaseStateBridge

    bridge = PhaseStateBridge()
    packet1 = {"psi": 0.8, "kappa": 0.3, "T": 0.9, "phi": 0.5}
    packet2 = {"psi": 0.81, "kappa": 0.32, "T": 0.92, "phi": 0.501}

    # Feed packets
    bridge.ingest(packet1)
    bridge.ingest(packet2)

    # ✅ CFA uses Greek-symbol keys
    greek_map = {"psi": "\u03c8", "kappa": "\u03ba", "phi": "\u03a6"}

    assert greek_map["psi"] in MockCFA.state, "CFA did not receive ψ"
    assert abs(MockCFA.state[greek_map["psi"]] - 0.81) < 1e-9
    assert abs(MockCFA.state[greek_map["phi"]] - 0.501) < 1e-9

    # ✅ Verify log file written
    log_path = "backend/logs/phase_state_events.jsonl"
    assert os.path.exists(log_path)
    with open(log_path, "r") as f:
        lines = [json.loads(x) for x in f.readlines()]
    assert len(lines) == 2
    assert "psi" in lines[0] and "phi" in lines[1]

    # ✅ Verify stability (Δφ small)
    assert bridge.verify_stability(tolerance=1e-2) is True