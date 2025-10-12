"""
Runtime Collapse Conservation Test (v0.4.4)
-------------------------------------------
Verifies μ preserves total energy & coherence within tolerance.
"""

import pytest
from backend.symatics.core.validators import law_check


class DummyCtx:
    def __init__(self):
        self.validate_runtime = True
        self.enable_trace = False


def test_collapse_conservation_passes():
    ctx = DummyCtx()
    expr = {
        "op": "μ",
        "pre_energy": 1.0,
        "energy": 1.005,
        "pre_coherence": 0.9,
        "coherence": 0.905,
        "tolerance": 0.02,
    }
    results = law_check.run_law_checks(expr, ctx)
    assert "collapse_conservation" in results
    assert results["collapse_conservation"]["passed"] is True


def test_collapse_conservation_detects_violation():
    ctx = DummyCtx()
    expr = {
        "op": "μ",
        "pre_energy": 1.0,
        "energy": 1.3,  # 30% drift
        "pre_coherence": 0.9,
        "coherence": 0.5,
        "tolerance": 0.02,
    }
    results = law_check.run_law_checks(expr, ctx)
    assert results["collapse_conservation"]["passed"] is False