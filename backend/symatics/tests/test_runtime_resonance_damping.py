"""
Runtime Resonance Damping Consistency Test (v0.3.7)
---------------------------------------------------
Validates Δf/f ≈ 1/(2Q) relation at runtime.
"""

from backend.symatics.core.validators import law_check


class DummyCtx:
    def __init__(self):
        self.validate_runtime = True
        self.enable_trace = False


def test_damping_consistency_passes():
    """Expected Δf/f ≈ 1/(2Q) within tolerance should pass."""
    ctx = DummyCtx()
    expr = {
        "op": "Q↯",
        "f_prev": 100.0,
        "f_curr": 105.0,   # 5% drift -> matches Q=10
        "Q": 10.0,
        "tolerance": 0.1,
    }
    results = law_check.run_law_checks(expr, ctx)
    assert "resonance_damping_consistency" in results
    assert results["resonance_damping_consistency"]["passed"] is True


def test_damping_consistency_fails_for_large_deviation():
    """Large Δf/f deviation should fail."""
    ctx = DummyCtx()
    expr = {
        "op": "Q↯",
        "f_prev": 100.0,
        "f_curr": 130.0,  # 30% drift
        "Q": 10.0,
        "tolerance": 0.05,
    }
    results = law_check.run_law_checks(expr, ctx)
    assert "resonance_damping_consistency" in results
    assert results["resonance_damping_consistency"]["passed"] is False