# backend/photon_algebra/tests/test_properties_t10_and_mixed_invariant.py
import pytest
from backend.photon_algebra.rewriter import normalize

# --- Small helpers -----------------------------------------------------------

EMPTY = {"op": "∅"}

def plus(a, b):
    return {"op": "⊕", "states": [a, b]}

def times(a, b):
    return {"op": "⊗", "states": [a, b]}

def entangle(a, b):
    return {"op": "↔", "states": [a, b]}

def neg(x):
    return {"op": "¬", "state": x}

def star(x):
    return {"op": "★", "state": x}

def is_plus_under_times(expr):
    """True iff any ⊗ node has an ⊕ child (should not happen post-normalize)."""
    if not isinstance(expr, dict):
        return False
    if expr.get("op") == "⊗":
        for s in expr.get("states", []):
            if isinstance(s, dict) and s.get("op") == "⊕":
                return True
    if "states" in expr:
        return any(is_plus_under_times(s) for s in expr["states"])
    if "state" in expr:
        return is_plus_under_times(expr["state"])
    return False

def normalize_to_fixpoint(e, max_iters: int = 4):
    """Run normalize a few times until it stabilizes (or hits max_iters)."""
    cur = normalize(e)
    for _ in range(max_iters - 1):
        nxt = normalize(cur)
        if nxt == cur:
            return cur
        cur = nxt
    return cur

# --- T10 samples (explicit) --------------------------------------------------

def test_T10_entanglement_distributivity_sample():
    # (a↔b) ⊕ (a↔c) → a ↔ (b ⊕ c)
    a, b, c = "a", "b", "c"
    left  = plus(entangle(a, b), entangle(a, c))
    right = entangle(a, plus(b, c))
    assert normalize(left) == normalize(right)

def test_T10_entanglement_distributivity_commuted():
    a, b, c = "a", "b", "c"
    left  = plus(entangle(a, c), entangle(a, b))
    right = entangle(a, plus(b, c))
    assert normalize(left) == normalize(right)

# --- Mixed invariant: no ⊕ directly under ⊗, with ★/¬/↔ present ------------

def test_no_plus_under_times_with_mixed_ops_examples():
    # Some hand-picked shapes
    e1 = times(plus("a", "b"), plus("c", "d"))
    e2 = plus(star(entangle("a", "b")), neg("c"))
    e3 = neg(plus(times("x", "y"), star("z")))
    e4 = plus(entangle("p","q"), entangle("p","r"))

    for e in [e1, e2, e3, e4]:
        n = normalize_to_fixpoint(e)
        assert not is_plus_under_times(n)

def test_no_plus_under_times_with_mixed_ops_property():
    hyp = pytest.importorskip("hypothesis")
    st  = pytest.importorskip("hypothesis.strategies")

    atoms = st.sampled_from(list("abcdxyz"))

    def trees(depth):
        if depth == 0:
            return atoms
        return st.one_of(
            atoms,
            st.builds(lambda x, y: plus(x, y),     trees(depth-1), trees(depth-1)),
            st.builds(lambda x, y: times(x, y),    trees(depth-1), trees(depth-1)),
            st.builds(lambda x, y: entangle(x, y), trees(depth-1), trees(depth-1)),
            st.builds(lambda x: neg(x),            trees(depth-1)),
            st.builds(lambda x: star(x),           trees(depth-1)),
        )

    @hyp.given(trees(4))
    @hyp.settings(max_examples=150)
    def _prop(e):
        # Allow up to a few passes to settle ★/↔ expansions before checking.
        n = normalize_to_fixpoint(e, max_iters=4)
        assert normalize(n) == n  # idempotent at fixpoint
        assert not is_plus_under_times(n)

    _prop()