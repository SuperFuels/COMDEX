import pytest
from backend.modules.glyphwave.qkd.qkd_policy_enforcer import QKDPolicyEnforcer
from backend.modules.photon.photon_algebra_runtime import PhotonAlgebraRuntime

def test_enforce_policy_non_required():
    enforcer = QKDPolicyEnforcer()
    wave_packet = {"qkd_policy": {"require_qkd": False}}
    assert enforcer.enforce_policy(wave_packet) is True

@pytest.mark.asyncio
async def test_photon_algebra_execution():
    runtime = PhotonAlgebraRuntime()
    capsule = {"name": "capsule_test", "glyphs": [{"operator": "⊕", "args": [], "meta": {}}]}
    result = await runtime.execute(capsule)  # ✅ now valid
    assert "final_wave" in result