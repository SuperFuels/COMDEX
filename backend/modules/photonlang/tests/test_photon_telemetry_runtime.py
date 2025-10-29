import pytest
from backend.modules.photonlang.interpreter import QuantumFieldCanvas

@pytest.mark.asyncio
async def test_photon_runtime_resonance():
    qfc = QuantumFieldCanvas()
    result = await qfc.resonate("⊕↔μ⟲", intensity=0.8, container_id="test_container")

    print("Resonance Output:", result)
    print("Telemetry Path should now exist under: artifacts/telemetry/")

    assert "seq" in result
    assert "⊕" in result["seq"]