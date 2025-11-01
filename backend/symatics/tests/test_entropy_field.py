# backend/symatics/tests/test_entropy_field.py
# ──────────────────────────────────────────────────────────────
# Tessaris SRK-3 - Unit Test: Entropy Field Model
# Verifies entropy computation, damping, and gradient stability.
# ──────────────────────────────────────────────────────────────

import numpy as np
import pytest
from backend.symatics.entropy_field import EntropyFieldState


class MockPhotonicField:
    """Minimal mock of photonic field exposing ψ values."""
    def __init__(self, psi_values):
        self.psi_values = psi_values


def test_entropy_increases_with_random_field():
    """Entropy should increase with randomization of ψ."""
    ef = EntropyFieldState()

    psi_low = np.ones(1000, dtype=complex)           # low-entropy field
    psi_high = np.random.randn(1000) + 1j*np.random.randn(1000)  # high-entropy field

    S_low = ef.compute_entropy(psi_low)
    S_high = ef.compute_entropy(psi_high)

    assert S_high > S_low, f"Expected higher entropy for randomized ψ: {S_high} <= {S_low}"


def test_entropy_damping_is_monotonic():
    """γ(S) should increase monotonically with S."""
    ef = EntropyFieldState()

    gamma_1 = ef.entropy_damping(0.1)
    gamma_2 = ef.entropy_damping(5.0)
    gamma_3 = ef.entropy_damping(10.0)

    assert gamma_1 < gamma_2 < gamma_3, "γ(S) must be monotonic increasing in S"


def test_entropy_update_populates_fields():
    """Update method should compute valid S and γ(S) from ψ."""
    psi = np.random.randn(500) + 1j * np.random.randn(500)
    field = MockPhotonicField(psi)

    ef = EntropyFieldState()
    ef.update(field)

    assert ef.S > 0, "Entropy S should be positive"
    assert 0.05 <= ef.gamma_S <= 0.2, f"γ(S) in unexpected range: {ef.gamma_S}"
    assert len(ef.history) > 0, "History should record at least one update step"


def test_entropy_gradient_sign_consistency():
    """∇S should reflect direction of entropy change."""
    ef = EntropyFieldState()
    grad_up = ef.entropy_gradient(1.0, 1.5)
    grad_down = ef.entropy_gradient(1.5, 1.0)

    assert grad_up > 0 and grad_down < 0, "∇S sign consistency failed"


if __name__ == "__main__":
    pytest.main([__file__])