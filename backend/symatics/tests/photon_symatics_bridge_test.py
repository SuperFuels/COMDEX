"""
🧪 Photon-Symatics Bridge Test - SRK-15 Task 1.1
Validates bidirectional translation and operator routing between symbolic
and photonic computation layers.
"""

import pytest
import asyncio
from backend.symatics.photon_symatics_bridge import PhotonSymaticsBridge


@pytest.mark.asyncio
async def test_sym_to_photon_execution():
    """Ensure symbolic expression executes correctly in photonic runtime."""
    bridge = PhotonSymaticsBridge()
    symbolic_expr = {
        "name": "test_capsule",
        "glyphs": [
            {"operator": "⊕", "args": [1, 2]},
            {"operator": "↔", "args": [0.5]},
            {"operator": "μ", "args": []},
        ],
    }

    result = await bridge.sym_to_photon(symbolic_expr)

    assert isinstance(result, dict)
    assert "final_wave" in result
    assert len(result["final_wave"]) == 3
    assert result["timestamp"] > 0


@pytest.mark.asyncio
async def test_photon_to_sym_conversion():
    """Verify conversion of photon result back to symbolic form."""
    bridge = PhotonSymaticsBridge()
    photon_state = {
        "final_wave": [0.2, 0.5, 0.3],
        "trace": [{"op": "⊕"}],
        "timestamp": 1730000000.0,
    }

    sym_form = await bridge.photon_to_sym(photon_state)
    assert sym_form["symbol"] == "Ψ"
    assert "amplitude_vector" in sym_form
    assert isinstance(sym_form["amplitude_vector"], list)
    assert sym_form["timestamp"] == photon_state["timestamp"]


def test_operator_resolution_photon_symbols():
    """Operators ⊕, ↔, ⟲, ∇, μ should resolve to photon runtime."""
    bridge = PhotonSymaticsBridge()
    for op in ["⊕", "↔", "⟲", "∇", "μ"]:
        runtime = bridge.resolve_operator(op)
        assert runtime.__class__.__name__ == "PhotonAlgebraRuntime"


def test_operator_resolution_symbolic_fallback():
    """Non-photonic operators should route to Symatic OPS registry."""
    bridge = PhotonSymaticsBridge()
    runtime = bridge.resolve_operator("π")
    assert hasattr(runtime, "apply")