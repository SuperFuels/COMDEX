"""
Runtime Collapse Energy Equivalence Test (v0.3.5)
-------------------------------------------------
Ensures that μ(⊕ψ₁,ψ₂) and ∇(⊕ψ₁,ψ₂) preserve energy equivalence
within a 1% tolerance under the runtime law validator.
"""

import pytest
from backend.symatics.core.validators import law_check


class DummyCtx:
    """Simple context for runtime validation tests."""
    def __init__(self, validate_runtime=True):
        self.validate_runtime = validate_runtime
        self.enable_trace = False


def test_collapse_energy_equivalence_passes():
    """Checks that identical μ/∇ energies are treated as equivalent."""
    ctx = DummyCtx()
    expr = {"op": "μ", "args": [{"op": "⊕", "args": ["ψ1", "ψ2"]}], "energy": 1.0}
    results = law_check.run_law_checks(expr, ctx)

    assert "collapse_energy_equivalence" in results
    outcome = results["collapse_energy_equivalence"]
    assert outcome["passed"] is True
    assert outcome["deviation"] < 0.01


def test_collapse_energy_equivalence_detects_drift():
    """Ensures energy drift >1% causes failure."""
    ctx = DummyCtx()

    # μ expression baseline energy
    expr_mu = {"op": "μ", "args": [{"op": "⊕", "args": ["ψ1", "ψ2"]}], "energy": 1.0}

    # ∇ variant with altered energy (simulated measurement drift)
    expr_nabla = {"op": "∇", "args": [{"op": "⊕", "args": ["ψ1", "ψ2"]}], "energy": 1.3}

    result_mu = law_check.law_collapse_energy_equivalence(expr_mu, ctx)
    result_nabla = law_check.law_collapse_energy_equivalence(expr_nabla, ctx)

    assert result_mu["passed"] is True
    assert result_nabla["passed"] is False or result_nabla["deviation"] > 0.01