# -*- coding: utf-8 -*-
"""
SRK-3 Integration Test — Field Entropy Kernel v1.2
─────────────────────────────────────────────────────────────
Ensures the SRK-3 entropy feedback system integrates
correctly with the Symatics Reasoning Kernel (SRK-1/2).

Validates:
  • Entropy increases with random ψ-fields
  • Damping γ(S) moderates λ(t) oscillations
  • SRK-3 diagnostics are available and populated
"""

import numpy as np
import pytest

from backend.symatics.core.srk_kernel import SymaticsReasoningKernel

@pytest.fixture(scope="module")
def srk():
    """Initialize the SRK kernel with SRK-3 extension loaded."""
    kernel = SymaticsReasoningKernel()
    assert hasattr(kernel, "extensions"), "SRK-3 extension list missing"
    assert any("SRK-3" in ext.name for ext in kernel.extensions), "SRK-3 not detected"
    return kernel


def test_entropy_increases_with_random_field(srk):
    """Entropy S should increase with randomized ψ(t) input."""
    from backend.symatics.entropy_field import EntropyFieldState

    ef = EntropyFieldState()
    psi1 = np.ones(1000, dtype=np.complex128)
    psi2 = np.random.randn(1000) + 1j * np.random.randn(1000)

    S1 = ef.compute_entropy(psi1)
    S2 = ef.compute_entropy(psi2)

    assert S2 > S1, f"Entropy did not increase with random field: S1={S1}, S2={S2}"


def test_entropy_feedback_damps_lambda_oscillation(srk):
    """Verify γ(S) reduces λ(t) oscillations in the SRK feedback loop."""
    initial_lambda = srk.lambda_t

    # Run multiple ψ-evaluations to trigger entropy feedback
    for _ in range(10):
        srk.superpose(np.random.rand(), np.random.rand())

    diag = srk.diagnostics()
    entropy_diag = diag.get("SRK-3 Entropy Field", {})
    gamma_S = entropy_diag.get("gamma_S", None)

    assert gamma_S is not None, "γ(S) not reported in diagnostics"
    assert 0.0 <= gamma_S < 1.0, f"γ(S) out of expected range: {gamma_S}"
    assert abs(srk.lambda_t - initial_lambda) < 0.2, "λ(t) diverged unexpectedly"


def test_entropy_diagnostics_available(srk):
    """Ensure SRK-3 diagnostics are merged correctly."""
    diag = srk.diagnostics()
    entropy_diag = diag.get("SRK-3 Entropy Field", None)

    assert entropy_diag is not None, "SRK-3 diagnostic block missing"
    assert "S" in entropy_diag and "gamma_S" in entropy_diag, "Missing entropy metrics"
    assert isinstance(entropy_diag["S"], float)
    assert isinstance(entropy_diag["gamma_S"], float)

    print("\n[SRK-3 Diagnostics]", entropy_diag)

# ─────────────────────────────────────────────────────────────
# SRK-3 — Entropy Regularization Runtime Law Test
# ─────────────────────────────────────────────────────────────
def test_entropy_regularization_law():
    """
    Verifies that the Field Entropy Regularization Law (SRK-3)
    passes under normal entropy–λ(t) conditions.
    """
    from backend.symatics.core.validators.law_check import law_entropy_regularization

    expr = {"op": "entropy_feedback", "S": 3.0, "lambda_t": 0.98, "lambda_prev": 1.0}
    result = law_entropy_regularization(expr)

    assert result["passed"], f"Entropy regularization failed: {result}"