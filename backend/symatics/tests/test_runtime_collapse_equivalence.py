"""
Runtime Law Validation — μ↔∇ Equivalence Test
----------------------------------------------
Ensures the runtime law validator (v0.3) correctly recognizes
μ(⊕a,b) ≡ ∇(⊕a,b) equivalence during live evaluation.

Covers both validation logic and CodexTrace emission stubs.
"""

import pytest

from backend.symatics.core.validators import law_check


class DummyCtx:
    """Minimal context emulating runtime flags."""
    def __init__(self, validate_runtime=True, enable_trace=False):
        self.validate_runtime = validate_runtime
        self.enable_trace = enable_trace


def test_runtime_collapse_equivalence_basic(monkeypatch):
    """Runtime μ↔∇ equivalence detection should pass on simple superposed states."""
    ctx = DummyCtx()

    mu_expr = {"op": "μ", "args": [{"op": "⊕", "args": ["ψ1", "ψ2"]}]}
    nabla_expr = {"op": "∇", "args": [{"op": "⊕", "args": ["ψ1", "ψ2"]}]}

    # Run both directions
    mu_results = law_check.run_law_checks(mu_expr, ctx)
    nabla_results = law_check.run_law_checks(nabla_expr, ctx)

    assert "collapse_equivalence" in mu_results
    assert mu_results["collapse_equivalence"]["passed"] is True
    assert "collapse_equivalence" in nabla_results
    assert nabla_results["collapse_equivalence"]["passed"] is True


def test_runtime_collapse_equivalence_non_superposed():
    """Should not mark μ↔∇ equivalent when inner op ≠ ⊕."""
    ctx = DummyCtx()
    mu_expr = {"op": "μ", "args": [{"op": "Δ", "args": ["ψ"]}]}
    results = law_check.run_law_checks(mu_expr, ctx)
    assert "collapse_equivalence" not in results


def test_runtime_collapse_equivalence_trace(monkeypatch):
    """Ensure CodexTrace telemetry is emitted when enabled."""
    emitted = {}

    def fake_record_event(event, **fields):
        emitted["event"] = event
        emitted["fields"] = fields
        return True

    monkeypatch.setattr(law_check, "record_event", fake_record_event)
    ctx = DummyCtx(enable_trace=True)

    expr = {"op": "μ", "args": [{"op": "⊕", "args": ["ψA", "ψB"]}]}
    _ = law_check.run_law_checks(expr, ctx)

    assert emitted["event"] == "law_check"
    assert "law" in emitted["fields"]
    assert "passed" in emitted["fields"]