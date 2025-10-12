# backend/symatics/tests/test_tensor_ops.py
import numpy as np
from backend.symatics.core.tensor_ops import (
    tensor_outer, tensor_contract, tensor_grad, tensor_measure, TensorEngine
)

def test_tensor_outer_and_contract(monkeypatch):
    events = []
    monkeypatch.setattr("backend.symatics.core.tensor_ops.record_event", lambda *a, **k: events.append(k))
    a, b = np.array([1, 2]), np.array([3, 4])
    outer = tensor_outer(a, b)
    assert outer.shape == (2, 2)
    contracted = tensor_contract(outer, axes=(0, 0))
    assert contracted.shape != ()
    assert events

def test_tensor_grad_and_measure():
    field = np.random.rand(4, 4)
    grad = tensor_grad(field)
    assert grad.shape == (4, 4, 2)
    norm = tensor_measure(grad)
    assert norm > 0

def test_tensor_engine_coupling_and_flux():
    engine = TensorEngine()
    # Non-uniform field — ensures nonzero gradient
    x = np.linspace(0, 1, 4)
    a = np.outer(x, x)        # gradient across ψ-space
    b = np.ones((4, 4)) * 2
    engine.register_field("law_a", a)
    engine.register_field("law_b", b)
    coupling = engine.compute_coupling("law_a", "law_b")
    assert coupling.shape == (4, 4, 4, 4)
    flux = engine.coherence_flux("law_a")
    assert flux > 0