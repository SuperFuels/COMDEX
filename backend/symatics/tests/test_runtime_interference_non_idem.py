"""
Runtime Interference Non-Idempotence Test (v0.4.3)
--------------------------------------------------
Ensures (A ⋈[φ] A) ≠ A for φ ≠ 0, π at runtime.
"""

import pytest
from backend.symatics.core.validators import law_check

class DummyCtx:
    def __init__(self):
        self.validate_runtime = True
        self.enable_trace = False


def test_non_idem_general_phase():
    ctx = DummyCtx()
    expr = {"op": "⋈", "args": ["ψA", "ψA", 1.57]}  # φ ≈ π/2
    results = law_check.run_law_checks(expr, ctx)
    assert "interference_non_idem" in results
    assert results["interference_non_idem"]["passed"] is True


def test_non_idem_trivial_zero():
    ctx = DummyCtx()
    expr = {"op": "⋈", "args": ["ψA", "ψA", 0.0]}
    results = law_check.run_law_checks(expr, ctx)
    assert results["interference_non_idem"]["passed"] is True  # allowed trivial case


def test_non_idem_trivial_pi():
    ctx = DummyCtx()
    expr = {"op": "⋈", "args": ["ψA", "ψA", 3.14159]}
    results = law_check.run_law_checks(expr, ctx)
    assert results["interference_non_idem"]["passed"] is True  # allowed trivial case