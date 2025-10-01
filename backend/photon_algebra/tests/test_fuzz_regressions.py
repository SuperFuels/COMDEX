# backend/photon_algebra/tests/test_fuzz_regressions.py

import pytest
from hypothesis import given, strategies as st
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.core import EMPTY

# --- Hypothesis strategies for random Photon expressions ---

def photon_atoms():
    """Generate atomic glyphs (a, b, c, …)."""
    return st.sampled_from(["a", "b", "c", "d", "e", "f", "g"])

def photon_exprs(max_depth=4):
    """Recursive strategy for PhotonState expressions."""
    if max_depth <= 0:
        return photon_atoms() | st.just(EMPTY)

    return st.recursive(
        photon_atoms() | st.just(EMPTY),
        lambda children: st.one_of(
            st.builds(lambda a, b: {"op": "⊕", "states": [a, b]}, children, children),
            st.builds(lambda a, b: {"op": "⊗", "states": [a, b]}, children, children),
            st.builds(lambda a: {"op": "¬", "state": a}, children),
            st.builds(lambda a, b: {"op": "⊖", "states": [a, b]}, children, children),
            st.builds(lambda a, b: {"op": "↔", "states": [a, b]}, children, children),
        ),
        max_leaves=10,
    )

# --- Property-based tests ---

@given(photon_exprs())
def test_normalize_idempotent(expr):
    """normalize() should be idempotent: normalize(normalize(e)) == normalize(e)."""
    n1 = normalize(expr)
    n2 = normalize(n1)
    assert n1 == n2

@given(photon_exprs())
def test_normalize_terminates(expr):
    """normalize() must terminate and not raise RecursionError."""
    normalize(expr)  # if it hangs or recurses infinitely, Hypothesis will catch