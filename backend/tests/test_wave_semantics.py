# backend/tests/test_wave_semantics.py
import math
import pytest

from backend.symatics.wave import Wave
from backend.symatics.operators import apply_operator


# ---------------------
# Fusion / Interference
# ---------------------

def test_fusion_constructive():
    """φ = 0 → amplitudes add directly."""
    w1 = Wave(frequency=10, amplitude=1.0, phase=0.0, polarization="H")
    w2 = Wave(frequency=10, amplitude=1.0, phase=0.0, polarization="H")
    fused = apply_operator("⋈", w1, w2, phi=0.0)
    assert pytest.approx(fused.amplitude, rel=1e-6) == 2.0


def test_fusion_destructive():
    """φ = π → perfect cancellation."""
    w1 = Wave(frequency=10, amplitude=1.0, phase=0.0, polarization="H")
    w2 = Wave(frequency=10, amplitude=1.0, phase=0.0, polarization="H")
    fused = apply_operator("⋈", w1, w2, phi=math.pi)
    assert pytest.approx(fused.amplitude, rel=1e-6) == 0.0


def test_fusion_arbitrary_phase():
    """Intermediate φ → cosine law of interference."""
    w1 = Wave(frequency=10, amplitude=1.0, phase=0.0, polarization="H")
    w2 = Wave(frequency=10, amplitude=1.0, phase=0.0, polarization="H")
    phi = math.pi / 3
    fused = apply_operator("⋈", w1, w2, phi=phi)
    expected = math.sqrt(1**2 + 1**2 + 2*1*1*math.cos(phi))
    assert pytest.approx(fused.amplitude, rel=1e-6) == expected


# ------------
# Resonance
# ------------

def test_resonance_near_match():
    """Frequencies almost identical → amplification > max input amplitude."""
    w1 = Wave(frequency=10.0000001, amplitude=1.0, phase=0.0, polarization="H")
    w2 = Wave(frequency=10.0, amplitude=2.0, phase=0.0, polarization="H")
    res = apply_operator("⟲", w1, w2)
    assert res.amplitude > max(w1.amplitude, w2.amplitude)
    assert res.meta["resonant"] is True
    assert res.meta["df"] <= 1e-6


def test_resonance_far_apart():
    """Frequencies far apart → amplitude should damp relative to stronger input."""
    w1 = Wave(frequency=10.0, amplitude=2.0, phase=0.0, polarization="H")
    w2 = Wave(frequency=20.0, amplitude=1.0, phase=0.0, polarization="H")
    res = apply_operator("⟲", w1, w2)
    assert res.amplitude < w1.amplitude
    assert res.meta["resonant"] is False
    assert res.meta["df"] == pytest.approx(abs(w1.frequency - w2.frequency))


# ----------
# Damping
# ----------

def test_damping_decay():
    """Exponential amplitude decay law should hold."""
    w = Wave(frequency=10.0, amplitude=1.0, phase=0.0, polarization="H")
    gamma = 0.1
    steps = 10
    damped = apply_operator("↯", w, gamma, steps=steps)

    expected = 1.0 * math.exp(-gamma * steps)
    assert damped.amplitude < w.amplitude
    assert pytest.approx(damped.amplitude, rel=1e-6) == expected
    assert damped.meta["damped"] is True
    assert damped.meta["gamma"] == gamma
    assert damped.meta["steps"] == steps