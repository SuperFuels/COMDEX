# tests/test_symatics_rulebook_v02.py
import pytest

from backend.symatics.symatics_rulebook import (
    check_all_laws,
    op_superpose,
    op_entangle,
    op_measure,
    op_project,
    op_derivative,
    op_integral,
)

# ──────────────────────────────
# v0.1 Regression Checks
# ──────────────────────────────

def test_commutativity_superpose():
    a, b = "x", "y"
    results = check_all_laws("⊕", a, b)
    assert results["commutativity"] is True

def test_associativity_superpose():
    a, b, c = "a", "b", "c"
    results = check_all_laws("⊕", a, b, c)
    assert results["associativity"] is True

def test_projection_law_applicable():
    seq = [[1, 2], 2, "x"]
    results = check_all_laws("π", seq, 0, 1)
    assert results["projection"] is True   # real match

def test_projection_law_vacuous():
    seq = [[1, 2, 3], [4, 5, 6]]
    results = check_all_laws("π", seq, 0, 1)
    assert results["projection"] is None

def test_integration_constant():
    results = check_all_laws("∫", "3", "x")
    assert results["integration_constant"] is True

# ──────────────────────────────
# v0.2 New Law Checks
# ──────────────────────────────

def test_interference_destructive():
    a, b = "ψ", "-ψ"
    results = check_all_laws("⊖", a, b)
    assert results["interference"] is True

def test_damping_exponential():
    state = "ψ"
    results = check_all_laws("↯", state, 0.1, 10)
    assert results["damping"] is True

def test_ghz_entanglement_symmetry():
    state = ["a", "b", "c"]
    results = check_all_laws("⊗GHZ", state)
    assert results["ghz_symmetry"] is True

def test_w_entanglement_symmetry():
    state = ["α", "β", "γ"]
    results = check_all_laws("⊗W", state)
    assert results["w_symmetry"] is True

def test_resonance_decay_qfactor():
    state = "ψ"
    results = check_all_laws("ℚ", state, 0.9, 10)
    assert results["resonance_decay"] is True

def test_measurement_noise():
    state = "ψ"
    results = check_all_laws("ε", state, 0.05)
    assert results["measurement_noise"] is True

# ──────────────────────────────
# Edge Cases
# ──────────────────────────────

def test_interference_non_cancel():
    a, b = "ψ1", "ψ2"
    results = check_all_laws("⊖", a, b)
    assert results["interference"] is True  # non-cancel case still valid law

def test_invalid_projection_index():
    seq = [1, 2]
    results = check_all_laws("π", seq, 5, 1)  # out of bounds
    assert results["projection"] is False