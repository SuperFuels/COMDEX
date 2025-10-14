"""
⚙️  Operator Overloading Layer Tests — SRK-15 Task 2
Verifies adaptive routing between Symatic OPS and PhotonAlgebraRuntime
based on coherence context.
"""

import pytest
import asyncio
from backend.symatics.operator_overloading_layer import OperatorOverloadingLayer


@pytest.mark.asyncio
async def test_photonic_dispatch_above_threshold():
    """Operators should route to PhotonAlgebraRuntime when coherence ≥ threshold."""
    layer = OperatorOverloadingLayer(coherence_threshold=0.7)
    layer.set_context(0.95)

    result = await layer.apply("⊕", 1, 2)
    assert "final_wave" in result
    assert result["trace"][0]["op"] == "⊕"


@pytest.mark.asyncio
async def test_symbolic_fallback_below_threshold():
    """Operators should route to symbolic OPS when coherence < threshold."""
    layer = OperatorOverloadingLayer(coherence_threshold=0.7)
    layer.set_context(0.4)

    # Minimal Signature-like mock
    class MockSignature:
        def __init__(self, polarization="H", amplitude=1.0, frequency=1.0, phase=0.0, mode="TE", oam_l=0, envelope=1.0):
            self.polarization = polarization
            self.amplitude = amplitude
            self.frequency = frequency
            self.phase = phase
            self.mode = mode
            self.oam_l = oam_l
            self.envelope = envelope
            self.meta = {}

    mock_sig = MockSignature("V")
    result = await layer.apply("π", mock_sig)
    assert result is not None
    assert hasattr(result, "polarization")
    assert hasattr(result, "amplitude")


@pytest.mark.asyncio
async def test_invalid_operator_raises_error():
    """Unknown operators should raise a ValueError."""
    layer = OperatorOverloadingLayer()
    with pytest.raises(ValueError):
        await layer.apply("❌", 1, 2)


@pytest.mark.asyncio
async def test_coherence_dynamic_switching():
    """Verify dynamic switching when coherence context changes."""
    layer = OperatorOverloadingLayer(coherence_threshold=0.6)

    layer.set_context(0.8)
    res1 = await layer.apply("↔", 0.5)
    assert "final_wave" in res1

    layer.set_context(0.2)

    class MockSignature:
        def __init__(self, polarization="H", amplitude=1.0, frequency=1.0, phase=0.0, mode="TE", oam_l=0, envelope=1.0):
            self.polarization = polarization
            self.amplitude = amplitude
            self.frequency = frequency
            self.phase = phase
            self.mode = mode
            self.oam_l = oam_l
            self.envelope = envelope
            self.meta = {}

    mock_sig = MockSignature("RHC")
    res2 = await layer.apply("π", mock_sig)
    assert res2 is not None
    assert hasattr(res2, "polarization")