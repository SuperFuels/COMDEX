# backend/tests/test_symatics_rulebook_v02.py
import pytest
from backend.symatics.symatics_rulebook import check_all_laws

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
# v0.2+ Cross-Law Tests
# ──────────────────────────────

@pytest.mark.parametrize("a,b,gamma,expected", [
    ("ψ1", "ψ2", 0.1, True),   # linear damping distributes
    ("ψ1", "ψ2", -0.5, False), # invalid gamma → fail
])
def test_damping_linearity(a, b, gamma, expected):
    results = check_all_laws("↯⊕", a, b, gamma)
    assert results["damping_linearity"] is expected


@pytest.mark.parametrize("seq,n,expected", [
    ([[1, 2], [3, 4]], 0, True),  # valid projection collapse consistency
    ([[1, 2], [3, 4]], 5, False), # out of range index → fail
])
def test_projection_collapse_consistency(seq, n, expected):
    results = check_all_laws("πμ", seq, n)
    assert results["projection_collapse_consistency"] is expected


@pytest.mark.parametrize("expr,q,gamma,expected", [
    ("ψ", 1.0, 0.1, True),    # valid resonance+damping
    ("ψ", -1.0, 0.1, False),  # invalid q → fail
    ("ψ", 1.0, -0.5, False),  # invalid gamma → fail
])
def test_resonance_damping_consistency(expr, q, gamma, expected):
    results = check_all_laws("ℚ↯", expr, q, gamma)
    assert results["resonance_damping_consistency"] is expected


# ──────────────────────────────
# Explicit Failure-Mode Tests
# ──────────────────────────────

def test_measurement_noise_out_of_range():
    state = "ψ"
    results = check_all_laws("ε", state, -0.2)  # epsilon < 0
    assert results["measurement_noise"] is False
    results = check_all_laws("ε", state, 1.2)   # epsilon > 1
    assert results["measurement_noise"] is False


def test_invalid_damping_factor():
    state = "ψ"
    results = check_all_laws("↯", state, -0.5, 10)  # gamma < 0
    assert results["damping"] is False


def test_invalid_ghz_symmetry():
    state = ["a", "b"]  # uneven GHZ (not 3+ states)
    results = check_all_laws("⊗GHZ", state)
    assert results["ghz_symmetry"] is False


def test_invalid_w_symmetry():
    state = ["α"]  # W requires multiple states
    results = check_all_laws("⊗W", state)
    assert results["w_symmetry"] is False


def test_invalid_resonance_qfactor():
    state = "ψ"
    results = check_all_laws("ℚ", state, -0.9, 10)  # invalid q
    assert results["resonance_decay"] is False


# ──────────────────────────────
# v0.2 Parametrized Law Checks
# ──────────────────────────────

@pytest.mark.parametrize("op,inputs,law_key,expected", [
    # v0.1 sanity
    ("⊕", ("x", "y"), "commutativity", True),
    ("⊕", ("a", "b", "c"), "associativity", True),
    ("∫", ("3", "x"), "integration_constant", True),

    # v0.2 single laws
    ("⊖", ("ψ", "-ψ"), "interference", True),   # destructive cancel
    ("⊖", ("ψ1", "ψ2"), "interference", True),  # non-cancel still valid
    ("↯", ("ψ", 0.1, 10), "damping", True),
    ("⊗GHZ", (["a", "b", "c"],), "ghz_symmetry", True),
    ("⊗W", (["α", "β", "γ"],), "w_symmetry", True),
    ("ℚ", ("ψ", 0.9, 10), "resonance_decay", True),
    ("ε", ("ψ", 0.05), "measurement_noise", True),   # valid epsilon
    ("ε", ("ψ", 1.5), "measurement_noise", False),   # out of range
])
def test_laws_parametrized(op, inputs, law_key, expected):
    results = check_all_laws(op, *inputs)
    assert results[law_key] is expected


# ──────────────────────────────
# Edge Cases
# ──────────────────────────────

def test_invalid_projection_index():
    seq = [1, 2]
    results = check_all_laws("π", seq, 5, 1)  # out of bounds
    assert results["projection"] is False

import pytest
from backend.symatics.symatics_rulebook import LAW_REGISTRY
from backend.symatics.operators import OPS
from backend.symatics.symatics_rulebook import _canonical


@pytest.mark.smoke
@pytest.mark.parametrize("op", ["⊗", "≡", "¬", "⊖"])
def test_operator_stub_exists(op):
    """Ensure v0.3 operator stubs exist in OPS."""
    assert op in OPS, f"{op} missing from OPS"


@pytest.mark.smoke
def test_calc_fundamental_theorem_stub():
    """Ensure calc_fundamental_theorem law stub is present in LAW_REGISTRY."""
    assert "calc_fundamental_theorem" in LAW_REGISTRY
    law = LAW_REGISTRY["calc_fundamental_theorem"]
    assert law["status"] == "stub"
    assert "Δ(∫(σ))" in law["description"]


@pytest.mark.smoke
@pytest.mark.parametrize("expr", [
    {"op": "⊗", "args": ["ψ1", "ψ2"]},
    {"op": "≡", "args": ["ψ1", "ψ2"]},
    {"op": "¬", "args": ["ψ"]},
    {"op": "⊖", "args": ["ψ1", "ψ2"]},
])
def test_canonicalization_does_not_crash(expr):
    """Canonicalization should handle new operator stubs without errors."""
    _ = _canonical(expr)  # no exception = pass