# backend/photon_algebra/tests/test_theorems.py
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.core import EMPTY  # 🔑 shared constant

def test_associativity():
    expr1 = {"op": "⊕", "states": [
        {"op": "⊕", "states": ["a", "b"]}, "c"
    ]}
    expr2 = {"op": "⊕", "states": [
        "a", {"op": "⊕", "states": ["b", "c"]}
    ]}
    assert normalize(expr1) == normalize(expr2)

def test_commutativity():
    expr1 = {"op": "⊕", "states": ["a", "b"]}
    expr2 = {"op": "⊕", "states": ["b", "a"]}
    assert normalize(expr1) == normalize(expr2)

def test_idempotence():
    expr = {"op": "⊕", "states": ["a", "a"]}
    assert normalize(expr) == "a"

def test_distributivity():
    expr = {"op": "⊗", "states": [
        "a", {"op": "⊕", "states": ["b", "c"]}
    ]}
    expected = {"op": "⊕", "states": [
        {"op": "⊗", "states": ["a", "b"]},
        {"op": "⊗", "states": ["a", "c"]},
    ]}
    assert normalize(expr) == normalize(expected)

def test_cancellation():
    expr = {"op": "⊖", "states": ["a", "a"]}
    assert normalize(expr) == EMPTY  # ✅ canonical ∅

def test_double_negation():
    expr = {"op": "¬", "state": {"op": "¬", "state": "a"}}
    assert normalize(expr) == "a"