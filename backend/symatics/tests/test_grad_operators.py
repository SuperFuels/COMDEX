# backend/symatics/tests/test_grad_operators.py
# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.6 - Gradient Operator Tests
# Validates ∇wave, ∇energy, ∇coherence and integration with ResonantLawEngine
# ──────────────────────────────────────────────────────────────

import pytest
import math
from backend.symatics.core.grad_operators import (
    grad_wave, grad_energy, grad_coherence, compute_gradients, update_resonant_field
)
from backend.symatics.core.resonant_laws import ResonantContext


def test_grad_wave_basic():
    g = grad_wave(1.0, 2.0, 0.0)
    assert math.isclose(g, 2.0, rel_tol=1e-6)


def test_grad_energy_positive():
    g = grad_energy(1.0, 1.5, dt=1.0)
    assert g == 0.5


def test_grad_coherence_wraparound():
    g = grad_coherence(0.0, math.pi / 2)
    assert 0 < g <= 1.0


def test_compute_gradients_returns_all_keys():
    t = {"energy": 1.0, "frequency": 1.0, "phase": 0.0}
    t1 = {"energy": 1.1, "frequency": 1.2, "phase": 0.3}
    grads = compute_gradients(t, t1)
    assert all(k in grads for k in ["grad_wave", "grad_energy", "grad_coherence"])


def test_update_resonant_field(monkeypatch):
    ctx = ResonantContext()
    events = []

    def mock_record_event(event_type, **kwargs):
        events.append((event_type, kwargs))

    monkeypatch.setattr("backend.symatics.core.grad_operators.record_event", mock_record_event)

    t = {"energy": 1.0, "phase": 0.0, "frequency": 1.0}
    t1 = {"energy": 1.1, "phase": 0.2, "frequency": 1.1}
    λ_new = update_resonant_field(ctx, "resonance_continuity", t, t1)

    assert isinstance(λ_new, float)
    assert any(ev[0] == "gradient_field_update" for ev in events)