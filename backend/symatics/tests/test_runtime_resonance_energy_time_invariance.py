"""
Runtime Resonance Energy–Time Invariance Test (v0.4.5)
------------------------------------------------------
Verifies that resonance systems conserve the energy–time product
(E*T ≈ constant) within 1% tolerance.
"""

import pytest
from backend.symatics.core.validators import law_check


class DummyCtx:
    def __init__(self):
        self.validate_runtime = True
        self.enable_trace = False


def test_energy_time_invariance_passes():
    ctx = DummyCtx()
    expr = {
        "op": "⟲t",
        "energy_prev": 1.0,
        "energy_curr": 0.99,
        "time_prev": 1.0,
        "time_curr": 1.01,
        "tolerance": 0.02,
    }
    results = law_check.run_law_checks(expr, ctx)
    assert "resonance_energy_time_invariance" in results
    assert results["resonance_energy_time_invariance"]["passed"] is True


def test_energy_time_invariance_detects_violation():
    ctx = DummyCtx()
    expr = {
        "op": "⟲t",
        "energy_prev": 1.0,
        "energy_curr": 1.3,
        "time_prev": 1.0,
        "time_curr": 0.7,
        "tolerance": 0.02,
    }
    results = law_check.run_law_checks(expr, ctx)
    assert results["resonance_energy_time_invariance"]["passed"] is False