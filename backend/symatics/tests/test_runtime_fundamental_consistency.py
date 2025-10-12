"""
Runtime Fundamental Theorem Consistency Test (v0.4.0)
-----------------------------------------------------
Checks that Δ(∫f) ≈ f and ∫(Δf) ≈ f within runtime tolerance.
"""

from backend.symatics.core.validators import law_check
import math


class DummyCtx:
    def __init__(self):
        self.validate_runtime = True
        self.enable_trace = False


def test_fundamental_consistency_passes():
    ctx = DummyCtx()
    # Sample function f(x) = sin(x)
    f_values = [math.sin(x) for x in [i * 0.01 for i in range(0, 500)]]
    expr = {"op": "calc_fundamental_theorem", "args": [f_values, 0.01]}
    results = law_check.run_law_checks(expr, ctx)

    assert "fundamental_consistency" in results
    assert results["fundamental_consistency"]["passed"] is True


def test_fundamental_consistency_detects_error():
    ctx = DummyCtx()
    # corrupted data (mismatch)
    f_values = [1.0 for _ in range(20)]
    expr = {"op": "calc_fundamental_theorem", "args": [f_values, 0.1]}
    results = law_check.run_law_checks(expr, ctx)

    assert "fundamental_consistency" in results
    assert results["fundamental_consistency"]["passed"] in (False, None)