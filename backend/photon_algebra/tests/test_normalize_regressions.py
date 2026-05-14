# backend/photon_algebra/tests/test_normalize_regressions.py
import pytest
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.rewriter import reset_normalize_memo as _reset_normalize_memo
_reset_normalize_memo()

def plus(a, b):
    return {"op": "⊕", "states": [a, b]}


def times(a, b):
    return {"op": "⊗", "states": [a, b]}


def is_plus_under_times(expr):
    """True if any ⊗ node has an ⊕ child (should not happen post-normalize)."""
    if not isinstance(expr, dict):
        return False
    if expr.get("op") == "⊗":
        for s in expr.get("states", []):
            if isinstance(s, dict) and s.get("op") == "⊕":
                return True
    # recurse
    if "states" in expr:
        return any(is_plus_under_times(s) for s in expr["states"])
    if "state" in expr:
        return is_plus_under_times(expr["state"])
    return False


# --- Deterministic regressions for T14-shaped inputs -------------------------

def test_dual_distributivity_terminates_and_idempotent():
    # α ⊕ (β ⊗ γ)
    a, b, c = "α", "β", "γ"
    expr = plus(a, times(b, c))
    n1 = normalize(expr)
    n2 = normalize(n1)
    assert n1 == n2
    assert not is_plus_under_times(n1)


def test_commuted_dual_distributivity_terminates_and_idempotent():
    # (β ⊗ γ) ⊕ α
    a, b, c = "α", "β", "γ"
    expr = plus(times(b, c), a)
    n1 = normalize(expr)
    n2 = normalize(n1)
    assert n1 == n2
    assert not is_plus_under_times(n1)


# --- Property: no ⊕ directly under ⊗ after normalize, and idempotence -------

def test_property_no_plus_under_times_random():
    hyp = pytest.importorskip("hypothesis")
    st = pytest.importorskip("hypothesis.strategies")

    atoms = st.sampled_from(list("abcxyz"))

    def exprs(max_depth):
        if max_depth == 0:
            return atoms
        return st.one_of(
            atoms,
            st.builds(lambda x, y: {"op": "⊕", "states": [x, y]},
                      exprs(max_depth - 1), exprs(max_depth - 1)),
            st.builds(lambda x, y: {"op": "⊗", "states": [x, y]},
                      exprs(max_depth - 1), exprs(max_depth - 1)),
        )

    @hyp.given(exprs(3))
    @hyp.settings(max_examples=100)
    def _prop(e):
        n = normalize(e)
        assert not is_plus_under_times(n)
        assert normalize(n) == n  # idempotence

    _prop()