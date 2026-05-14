import pytest, asyncio
from backend.modules.sci.sci_core import SCIRuntimeGateway

@pytest.mark.asyncio
async def test_run_photon_source():
    gw = SCIRuntimeGateway(container_id="test_runtime")
    src = 'canvas = QuantumFieldCanvas(); canvas.resonate("⊕↔μ⟲", intensity=0.8)'
    result = await gw.run_photon_source(src)
    assert result["ok"]
    assert "telemetry_path" in result