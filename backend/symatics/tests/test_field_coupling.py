# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.7 — Integration Test
# FieldCouplingEngine Stability & Coherence Validation
# ──────────────────────────────────────────────────────────────

import numpy as np
import pytest
from backend.symatics.core.field_coupling_engine import FieldCouplingEngine
from backend.symatics.core.flow_operators import coherence_flux


def test_field_coupling_stability():
    """Verify λ↔ψ co-evolution maintains bounded energy and coherence."""
    engine = FieldCouplingEngine(viscosity=0.02, damping=0.01, eta=0.05)

    # Initialize wave and law fields
    ψ0 = np.sin(np.linspace(0, np.pi, 128))
    λ0 = np.ones_like(ψ0)

    engine.register_field("ψ", ψ0)
    engine.register_field("λ", λ0)

    energy_trace, coherence_trace = [], []

    for t in range(100):
        ψ_prev = engine.fields["ψ"].copy()
        λ_prev = engine.fields["λ"].copy()

        # Step evolution
        ψ_next, λ_next = engine.step("ψ", "λ", dt=0.1)

        # Energy = ∫ψ², Coherence = ⟨e^{-||∇ψ||}⟩
        energy = np.sum(ψ_next ** 2)
        flux = coherence_flux(ψ_next)
        coherence = np.mean(np.abs(flux))

        energy_trace.append(energy)
        coherence_trace.append(coherence)

        # Stability assertions
        assert np.all(np.isfinite(ψ_next))
        assert np.all(np.isfinite(λ_next))
        assert 0.0 <= np.mean(λ_next) <= 2.5

    # Post-run validation: energy should decay, coherence remain bounded
    assert energy_trace[-1] < energy_trace[0] * 1.1
    assert 0.0 <= np.mean(coherence_trace) <= 1.0


def test_field_coupling_summary():
    """Check summary statistics of mean λ and ψ values."""
    engine = FieldCouplingEngine()
    ψ0 = np.sin(np.linspace(0, np.pi, 32))
    λ0 = np.ones_like(ψ0)
    engine.register_field("ψ", ψ0)
    engine.register_field("λ", λ0)
    for _ in range(10):
        engine.step("ψ", "λ", dt=0.05)
    summary = engine.summary()
    assert "mean_lambda" in summary and "mean_psi" in summary
    assert 0.0 <= summary["mean_lambda"] <= 2.0
    assert np.isfinite(summary["mean_psi"])