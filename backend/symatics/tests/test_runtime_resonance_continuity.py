"""
Runtime Resonance Continuity Test (v0.3.6)
------------------------------------------
Verifies that ⟲ (resonance) operations maintain amplitude & phase continuity
across timesteps within tolerance.
"""

from backend.symatics.core.validators import law_check


class DummyCtx:
    def __init__(self):
        self.validate_runtime = True
        self.enable_trace = False


def test_resonance_continuity_passes():
    ctx = DummyCtx()
    expr = {
        "op": "⟲",
        "amplitude": [1.00, 1.02],
        "phase": [0.0, 0.05],
        "tolerance": 0.05,
    }
    results = law_check.run_law_checks(expr, ctx)
    assert "resonance_continuity" in results
    assert results["resonance_continuity"]["passed"] is True


def test_resonance_continuity_fails_on_large_drift():
    ctx = DummyCtx()
    expr = {
        "op": "⟲",
        "amplitude": [1.0, 1.3],     # 30% drift
        "phase": [0.0, 1.0],         # large phase shift
        "tolerance": 0.05,
    }
    results = law_check.run_law_checks(expr, ctx)
    assert "resonance_continuity" in results
    assert results["resonance_continuity"]["passed"] is False