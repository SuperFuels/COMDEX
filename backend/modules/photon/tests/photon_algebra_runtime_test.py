import pytest
from backend.modules.photon.photon_algebra_runtime import PhotonAlgebraRuntime

@pytest.mark.asyncio
async def test_photon_algebra_execution():
    runtime = PhotonAlgebraRuntime()
    capsule = {
        "name": "capsule_test",
        "glyphs": [
            {"operator": "⊕", "args": [], "meta": {}},
            {"operator": "↔", "args": [], "meta": {}},
            {"operator": "μ", "args": [], "meta": {}},
        ],
    }
    result = await runtime.execute(capsule)  # ✅ now inside async def
    assert "final_wave" in result