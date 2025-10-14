import pytest
from backend.modules.holograms.ghx_trace_encoder import GHXTraceEncoder

@pytest.mark.asyncio
async def test_trace_encoding_and_verification():
    encoder = GHXTraceEncoder()
    usr_telemetry = {
        "coherence": 0.82,
        "avg_coherence": 0.80,
        "mode_ratio": {"photon": 0.6, "symbolic": 0.4},
        "telemetry_count": 12,
        "recent": [0.82, 0.81, 0.79]
    }

    trace = encoder.encode(usr_telemetry)
    assert "entropy_signature" in trace
    assert encoder.verify_trace(trace)
    assert 0 <= trace["stability_index"] <= 1