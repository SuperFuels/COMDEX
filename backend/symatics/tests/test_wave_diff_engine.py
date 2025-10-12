# backend/symatics/tests/test_wave_diff_engine.py
import numpy as np
from backend.symatics.core.wave_diff_engine import (
    d_dt, laplacian, integrate_wave, evolve_wavefield, WaveDiffEngine
)

def test_d_dt_basic():
    t = np.zeros((3, 3))
    t1 = np.ones((3, 3))
    dt_field = d_dt(t, t1)
    assert np.allclose(dt_field, 1.0)

def test_laplacian_returns_nonzero():
    x = np.linspace(0, np.pi, 5)
    y = np.linspace(0, np.pi, 5)
    X, Y = np.meshgrid(x, y)
    f = np.sin(X) * np.cos(Y)  # nonlinear field
    lap = laplacian(f)
    assert lap.shape == f.shape
    assert not np.allclose(lap, 0)

def test_integrate_wave_positive():
    f = np.ones((4, 4))
    val = integrate_wave(f)
    assert val > 0

def test_evolve_wavefield_reduces_amplitude():
    ψ = np.ones((5, 5))
    λ = np.ones_like(ψ) * 0.5
    ψ_next = evolve_wavefield(ψ, λ, dt=0.1, damping=0.1)
    assert ψ_next.shape == ψ.shape
    assert np.mean(ψ_next) < np.mean(ψ)

def test_wave_diff_engine_end_to_end():
    ψ = np.ones((5, 5))
    λ = np.ones_like(ψ) * 0.2
    engine = WaveDiffEngine()
    engine.register_field("psi", ψ)
    engine.register_field("lambda", λ)

    before = engine.measure_energy("psi")
    ψ_next = engine.step("psi", "lambda", dt=0.05)
    after = engine.measure_energy("psi")

    assert ψ_next.shape == ψ.shape
    assert after < before
    coherence = engine.coherence_index("psi")
    assert 0 <= coherence <= 1