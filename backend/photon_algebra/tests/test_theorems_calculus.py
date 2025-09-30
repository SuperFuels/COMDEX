# backend/photon_algebra/tests/test_theorems_calculus.py
import pytest
from backend.photon_algebra import core, theorems, rewriter

# -------------------------------
# Sample states for testing
# -------------------------------
def sample_states():
    return ["α", "β", "γ", core.EMPTY]


# -------------------------------
# T13 — Absorption
# -------------------------------
@pytest.mark.parametrize("a,b", [
    ("α", "β"),
    ("x", "y"),
    ("a", core.EMPTY),
])
def test_T13_absorption(a, b):
    assert theorems.theorem_T13(a, b)


# -------------------------------
# T14 — Dual distributivity
# -------------------------------
@pytest.mark.parametrize("a,b,c", [
    ("α", "β", "γ"),
    ("a", "b", core.EMPTY),
])
def test_T14_dual_distributivity(a, b, c):
    assert theorems.theorem_T14(a, b, c)


# -------------------------------
# T15 — Falsification
# -------------------------------
@pytest.mark.parametrize("a", sample_states())
def test_T15_falsification(a):
    assert theorems.theorem_T15(a)