# backend/symatics/tests/test_calc_ops.py
import numpy as np
from backend.symatics.core.calc_ops import (
    grad_lambda, div_lambda, curl_psi, continuity_eq, CalculusEngine
)

def test_grad_and_div_nonzero():
    field = np.outer(np.linspace(0, 1, 5), np.linspace(0, 1, 5))
    grad = grad_lambda(field)
    div = div_lambda(field)
    assert grad.shape == (5, 5, 2)
    assert np.any(div != 0)

def test_curl_behavior():
    field = np.sin(np.linspace(0, np.pi, 5))[:, None] * np.cos(np.linspace(0, np.pi, 5))[None, :]
    curl = curl_psi(field)
    assert curl.shape == (5, 5)
    assert np.allclose(np.mean(curl), 0, atol=1)

def test_continuity_equation_residual():
    λ = np.outer(np.linspace(0, 1, 5), np.linspace(0, 1, 5))
    ψ = np.ones_like(λ)
    residual = continuity_eq(λ, ψ)
    assert residual >= 0

def test_calculus_engine_end_to_end():
    engine = CalculusEngine()
    λ = np.outer(np.linspace(0, 1, 4), np.linspace(0, 1, 4))
    ψ = np.random.rand(4, 4)
    engine.register_field("lambda", λ)
    engine.register_field("psi", ψ)
    profile = engine.differential_profile("lambda")
    assert all(k in profile for k in ["grad", "div", "curl"])
    res = engine.continuity_residual("lambda", "psi")
    assert isinstance(res, float)