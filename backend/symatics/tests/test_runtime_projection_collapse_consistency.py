"""
Runtime Projection–Collapse Consistency Test (v0.3.9)
-----------------------------------------------------
Validates that π(μ(ψ)) ≈ μ(π(ψ)) under runtime law evaluation.
"""

from backend.symatics.core.validators import law_check


class DummyCtx:
    def __init__(self):
        self.validate_runtime = True
        self.enable_trace = False


def test_projection_collapse_consistency_passes():
    ctx = DummyCtx()
    expr = {"op": "πμ", "args": [["ψ1", "ψ2", "ψ3"], 1]}
    results = law_check.run_law_checks(expr, ctx)

    assert "projection_collapse_consistency" in results
    outcome = results["projection_collapse_consistency"]
    assert outcome["passed"] is True
    assert "holds" in outcome["details"]


def test_projection_collapse_consistency_invalid_args():
    ctx = DummyCtx()
    expr = {"op": "πμ", "args": [["ψ1", "ψ2"]]}  # missing index
    results = law_check.run_law_checks(expr, ctx)

    assert "projection_collapse_consistency" in results
    assert results["projection_collapse_consistency"]["passed"] is False