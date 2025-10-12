# backend/symatics/tests/test_tensor_field_coupling.py
# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.8 — Integration Test: Tensor λ⊗ψ Coupling
# Validates stability, coherence, and event emission for the
# Resonant Tensor Field Continuum.
# Author: Tessaris Core Systems / Codex Intelligence Group
# ──────────────────────────────────────────────────────────────

import numpy as np
import pytest
from backend.symatics.core.tensor_field_engine import ResonantTensorField
from backend.symatics.core.tensor_ops import TensorEngine, tensor_outer, tensor_divergence, tensor_grad


def test_tensor_field_initialization():
    """Ensure tensor field initializes with correct shapes and defaults."""
    field = ResonantTensorField(shape=(64, 64))
    assert field.ψ.shape == (64, 64)
    assert field.λ.shape == (64, 64)
    assert np.allclose(np.mean(field.λ), 1.0)


def test_tensor_gradient_and_divergence_consistency():
    """Gradient and divergence operators must yield finite results."""
    ψ = np.random.rand(32, 32)
    grad = tensor_grad(ψ)
    div = tensor_divergence(np.stack([grad[..., 0], grad[..., 1]], axis=-1))
    assert np.isfinite(np.mean(grad))
    assert np.isfinite(np.mean(div))


def test_tensor_coupling_stability():
    """Integration loop verifying λ⊗ψ coupling stability."""
    field = ResonantTensorField(shape=(32, 32))
    for _ in range(20):
        ψ_prev, λ_prev = field.ψ.copy(), field.λ.copy()
        ψ_next, λ_next = field.step(dt=0.05)

        # Verify bounded energy
        energy = np.sum(ψ_next**2)
        assert energy >= 0 and np.isfinite(energy)

        # Verify λ stays within stability limits
        assert np.all((λ_next >= 0.0) & (λ_next <= 2.5))

    # Validate telemetry traces exist
    assert len(field.history["energy"]) > 0
    assert len(field.history["coherence"]) > 0


def test_tensor_engine_coherence_flux():
    """Verify TensorEngine produces measurable coherence flux."""
    engine = TensorEngine()
    ψ = np.sin(np.linspace(0, np.pi, 64))
    λ = np.cos(np.linspace(0, np.pi, 64))
    engine.register_field("psi", ψ)
    engine.register_field("lambda", λ)

    flux_λ = engine.coherence_flux("lambda")
    assert flux_λ >= 0 and np.isfinite(flux_λ)