"""
🧪 Unified Symbolic Runtime Tests — SRK-15 Task 3
Validates hybrid symbolic–photonic orchestration, coherence-aware routing,
and temporal execution sequences.
"""

import pytest
import asyncio
import time
from backend.symatics.unified_symbolic_runtime import UnifiedSymbolicRuntime


@pytest.mark.asyncio
async def test_photonic_capsule_execution():
    """Photon capsule expressions should route to photonic runtime."""
    usr = UnifiedSymbolicRuntime()
    usr.set_context(0.9)

    capsule = {
        "name": "test_capsule_usr",
        "glyphs": [
            {"operator": "⊕", "args": [1, 2]},
            {"operator": "↔", "args": [0.3]},
            {"operator": "μ", "args": []},
        ],
    }

    result = await usr.execute(capsule)
    assert result["mode"] == "photonic"
    assert "final_wave" in result
    assert isinstance(result["trace"], list)
    assert 0.0 <= result["coherence"] <= 1.0


@pytest.mark.asyncio
async def test_symbolic_operator_dispatch_low_coherence():
    """Low coherence should route execution through symbolic OPS layer."""
    usr = UnifiedSymbolicRuntime(coherence_threshold=0.7)
    usr.set_context(0.3)

    # π is symbolic (projection)
    result = await usr.execute("π", 1.0)
    assert result["mode"] == "symbolic"
    assert "result" in result
    assert result["coherence"] < 0.7


@pytest.mark.asyncio
async def test_photonic_operator_dispatch_high_coherence():
    """High coherence should trigger photonic execution path."""
    usr = UnifiedSymbolicRuntime(coherence_threshold=0.6)
    usr.set_context(0.95)

    result = await usr.execute("↔", 0.5)
    assert result["mode"] == "photon"
    assert "final_wave" in result.get("result", result) or "result" in result


@pytest.mark.asyncio
async def test_sequence_evaluation_flow():
    """Sequential operator execution should preserve coherence context."""
    usr = UnifiedSymbolicRuntime(coherence_threshold=0.5)
    usr.set_context(0.8)

    seq = [
        ("⊕", 1),
        ("↔", 0.5),
        ("π", 1.0),
    ]

    result = await usr.evaluate_sequence(seq)
    assert "sequence_results" in result
    assert len(result["sequence_results"]) == 3
    assert result["coherence"] == pytest.approx(0.8, rel=1e-6)


@pytest.mark.asyncio
async def test_invalid_input_type_raises():
    """Invalid expression types should raise TypeError."""
    usr = UnifiedSymbolicRuntime()
    with pytest.raises(TypeError):
        await usr.execute(42)  # not a dict or str