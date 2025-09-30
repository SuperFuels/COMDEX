# backend/photon_algebra/tests/test_theorems_calculus.py
import pytest
from backend.photon_algebra import core, theorems, rewriter

# -------------------------------
# Sample states for testing
# -------------------------------
def sample_states():
    # include EMPTY and a few atoms; we keep it simple on purpose
    return ["α", "β", "γ", core.EMPTY]


# -------------------------------
# T13 — Absorption
#   a ⊕ (a ⊗ b) == a
#   (a ⊗ b) ⊕ a == a  (left form)
# -------------------------------
@pytest.mark.parametrize("a,b", [
    ("α", "β"),
    ("x", "y"),
    ("a", core.EMPTY),
])
def test_T13_absorption_right(a, b):
    assert theorems.theorem_T13(a, b)

@pytest.mark.parametrize("a,b", [
    ("α", "β"),
    ("x", "y"),
    ("a", core.EMPTY),
])
def test_T13_absorption_left(a, b):
    # Explicitly check the left variant via normalize()
    lhs = {"op": "⊕", "states": [
        {"op": "⊗", "states": [a, b]},
        a
    ]}
    assert rewriter.normalize(lhs) == rewriter.normalize(a)


# -------------------------------
# T14 — Dual distributivity
#   a ⊕ (b ⊗ c) == (a ⊕ b) ⊗ (a ⊕ c)
# -------------------------------
@pytest.mark.parametrize("a,b,c", [
    ("α", "β", "γ"),
    ("a", "b", core.EMPTY),
])
def test_T14_dual_distributivity(a, b, c):
    assert theorems.theorem_T14(a, b, c)


# -------------------------------
# T15 — Falsification
#   a ⊖ ∅ == a
#   ∅ ⊖ a == a  (symmetric form)
# -------------------------------
@pytest.mark.parametrize("a", sample_states())
def test_T15_falsification_right(a):
    assert theorems.theorem_T15(a)

@pytest.mark.parametrize("a", sample_states())
def test_T15_falsification_left(a):
    lhs = {"op": "⊖", "states": [core.EMPTY, a]}
    assert rewriter.normalize(lhs) == rewriter.normalize(a)