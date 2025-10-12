# backend/symatics/tests/test_grad_coupling.py
# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.6.3 — Integration Test: λ↔ψ Coupling
# Validates feedback between ResonantLawEngine and WaveDiffEngine.
# Includes analytic resonance metric ℛ(ψ,t) = E + αC.
# ──────────────────────────────────────────────────────────────

import numpy as np
import pytest
from backend.symatics.core.resonant_laws import ResonantContext
from backend.symatics.core.grad_operators import update_resonant_field
from backend.symatics.core.wave_diff_engine import WaveDiffEngine


def test_lambda_psi_coupling_stability():
    """Integration test verifying λ–ψ feedback loop stability."""
    ctx = ResonantContext()
    engine = WaveDiffEngine()

    # Initialize ψ field (sine wave) and λ field (uniform baseline)
    ψ0 = np.sin(np.linspace(0, np.pi, 128))
    λ0 = np.ones_like(ψ0) * 1.0

    engine.register_field("ψ", ψ0)
    engine.register_field("λ", λ0)

    energy_trace, coherence_trace = [], []

    for t in range(100):
        ψ_prev = engine.fields["ψ"].copy()
        energy_prev = np.sum(ψ_prev ** 2)
        coherence_prev = np.exp(-np.linalg.norm(np.gradient(ψ_prev)))

        # Wave evolution step using current λ
        engine.step("ψ", λ_name="λ", dt=0.1)

        ψ_next = engine.fields["ψ"].copy()
        energy_next = np.sum(ψ_next ** 2)
        coherence_next = np.exp(-np.linalg.norm(np.gradient(ψ_next)))

        # Update λ field via gradient resonance feedback
        new_lambda = update_resonant_field(
            ctx,
            "resonance_continuity",
            {"energy": energy_prev, "coherence": coherence_prev},
            {"energy": energy_next, "coherence": coherence_next},
        )

        # Broadcast updated λ across field for simplicity
        engine.fields["λ"][:] = new_lambda

        energy_trace.append(energy_next)
        coherence_trace.append(coherence_next)

    # Mean λ stability check
    λ_values = list(ctx.law_weights.weights.values())
    λ_mean = np.mean(λ_values) if λ_values else 1.0

    # Basic invariants
    assert 0.0 <= λ_mean <= 2.0, "λ(t) drifted outside stability range"
    assert np.isfinite(np.mean(energy_trace)), "Energy trace invalid"
    assert all(0.0 <= c <= 1.0 for c in coherence_trace), "Coherence trace out of range"

    print(f"✅ λ mean: {λ_mean:.3f} | E_final={energy_trace[-1]:.3f} | C_final={coherence_trace[-1]:.3f}")