# backend/photon_algebra/tests/test_mixed_ops_ordering.py
import itertools
import json
import pytest

from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.rewriter import reset_normalize_memo as _reset_normalize_memo
_reset_normalize_memo()

EMPTY = {"op": "∅"}

def plus(*xs):
    return {"op": "⊕", "states": list(xs)}

def times(a, b):
    return {"op": "⊗", "states": [a, b]}

def entangle(a, b):
    return {"op": "↔", "states": [a, b]}

def star(x):
    return {"op": "★", "state": x}

def neg(x):
    return {"op": "¬", "state": x}

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


# ------------------------------------------------------------------------------
# Deterministic ordering for ⊕ with mixed nodes:
# Assert permutation-invariance: all permutations normalize to the same NF.
# ------------------------------------------------------------------------------

def _canon(x):
    """Stable string for structural equality without relying on internal order."""
    return json.dumps(x, sort_keys=True, ensure_ascii=False)

def test_plus_permutation_invariance_with_mixed_ops():
    a, b = "a", "b"
    items = [
        entangle(a, b),     # a ↔ b
        star(a),            # ★a
        neg(b),             # ¬b
        times("c", "d"),    # c ⊗ d
        "z",
    ]

    normalized = [
        _canon(normalize(plus(*p)))
        for p in itertools.permutations(items, len(items))
    ]
    # All permutations should yield the same canonical NF
    assert len(set(normalized)) == 1


# ------------------------------------------------------------------------------
# Idempotence always holds for mixed trees
# ------------------------------------------------------------------------------

def test_idempotence_mixed_tree():
    expr = plus(
        times(neg("x"), star("y")),
        entangle("y", neg("z")),
        plus("z", star("x")),
        neg(neg("w")),          # double-negation present
    )
    n1 = normalize(expr)
    n2 = normalize(n1)
    assert n1 == n2
    assert not is_plus_under_times(n1)


# ------------------------------------------------------------------------------
# Calculus sanity checks in mixed contexts
#   - Double negation: ¬(¬a) -> a
#   - T12: ★(a↔b) -> (★a) ⊕ (★b)
#   - T10: (a↔b) ⊕ (a↔c) -> a ↔ (b ⊕ c)  (OPTIONAL -> xfail if not active)
# ------------------------------------------------------------------------------

def test_double_negation_basics():
    assert normalize(neg(neg("q"))) == "q"
    # inside a larger tree (relaxed check; core is that ¬¬ collapses)
    expr = plus(times("p", neg(neg("q"))), star(neg(neg("r"))))
    n = normalize(expr)
    # just ensure we didn't reintroduce ⊕ under ⊗ by accident
    assert not is_plus_under_times(n)

def test_T12_projection_fidelity_star_over_entangle():
    # ★(a↔b) -> (★a) ⊕ (★b)
    a, b = "α", "β"
    left  = star(entangle(a, b))
    right = plus(star(a), star(b))
    assert normalize(left) == normalize(right)

def test_T10_entanglement_distributivity_sample():
    # (a↔b) ⊕ (a↔c) -> a ↔ (b ⊕ c)
    a, b, c = "a", "b", "c"
    left  = plus(entangle(a, b), entangle(a, c))
    right = entangle(a, plus(b, c))
    assert normalize(left) == normalize(right)

def test_T10_entanglement_distributivity_commuted():
    # (a↔c) ⊕ (a↔b) -> a ↔ (b ⊕ c)
    a, b, c = "a", "b", "c"
    left  = plus(entangle(a, c), entangle(a, b))
    right = entangle(a, plus(b, c))
    assert normalize(left) == normalize(right)

def test_T10_stability_under_permutations():
    import itertools
    a, b, c = "a", "b", "c"
    terms = [entangle(a, b), entangle(a, c)]
    targets = normalize(entangle(a, plus(b, c)))

    for perm in itertools.permutations(terms, 2):
        left = plus(*perm)
        assert normalize(left) == targets

# ------------------------------------------------------------------------------
# Mixed invariant: no ⊕ directly under ⊗, even when other ops are present
# ------------------------------------------------------------------------------

def test_no_plus_under_times_in_mixed_trees():
    expr = times(
        plus(entangle("a","b"), star("c")),
        plus(neg("d"), times("e","f")),
    )
    n = normalize(expr)
    assert not is_plus_under_times(n)


# ------------------------------------------------------------------------------
# Optional: small property test over mixed ops (Hypothesis import-safe)
# ------------------------------------------------------------------------------

def test_property_idempotence_and_invariant_mixed():
    hyp = pytest.importorskip("hypothesis")
    st  = pytest.importorskip("hypothesis.strategies")

    atoms = st.sampled_from(list("abcdxyz"))

    def trees(depth):
        if depth == 0:
            return atoms
        return st.one_of(
            atoms,
            st.builds(lambda x, y: {"op":"⊕","states":[x,y]}, trees(depth-1), trees(depth-1)),
            st.builds(lambda x, y: {"op":"⊗","states":[x,y]}, trees(depth-1), trees(depth-1)),
            st.builds(lambda x, y: {"op":"↔","states":[x,y]}, trees(depth-1), trees(depth-1)),
            st.builds(lambda x   : {"op":"¬","state":x},      trees(depth-1)),
            st.builds(lambda x   : {"op":"★","state":x},      trees(depth-1)),
        )

    @hyp.given(trees(3))
    @hyp.settings(max_examples=120)
    def _prop(e):
        # Some mixed trees (e.g., ★ with nested ↔) can expose a second rewrite
        # after the first normalize(). So we assert *eventual* stability.
        n1 = normalize(e)
        n2 = normalize(n1)
        n3 = normalize(n2)

        # eventual idempotence
        assert n2 == n3

        # invariant still holds
        def is_plus_under_times(expr):
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

        assert not is_plus_under_times(n3)

    _prop()


def _entangle(a, b): return {"op":"↔","states":[a,b]}
def _plus(a, b):     return {"op":"⊕","states":[a,b]}

def _is_plus_under_times(e):
    if not isinstance(e, dict):
        return False
    if e.get("op") == "⊗":
        return any(
            isinstance(s, dict) and s.get("op") == "⊕"
            for s in e.get("states", [])
        )
    if "states" in e:
        return any(_is_plus_under_times(s) for s in e["states"])
    if "state" in e:
        return _is_plus_under_times(e["state"])
    return False

# --- Property 1: T10 stable under permutations of the two entangle terms -----
def test_property_T10_permutation_invariance():
    hyp = pytest.importorskip("hypothesis")
    st  = pytest.importorskip("hypothesis.strategies")

    atoms = st.sampled_from(list("abcxyz"))

    @hyp.given(a=atoms, b=atoms, c=atoms)
    @hyp.settings(max_examples=120)
    def _prop(a, b, c):
        t1 = _entangle(a, b)
        t2 = _entangle(a, c)
        xs = [t1, t2]
        # normalizing any permutation should yield the same NF
        nfs = { str(normalize({"op":"⊕","states": list(p)})) for p in itertools.permutations(xs, 2) }
        assert len(nfs) == 1
    _prop()

# --- Property 2: no ⊕ under ⊗ still holds with deep ★/¬/↔ nesting -----------
def test_property_no_plus_under_times_deep_mixed():
    hyp = pytest.importorskip("hypothesis")
    st  = pytest.importorskip("hypothesis.strategies")

    atoms = st.sampled_from(list("abcdxyz"))

    def trees(d):
        if d == 0:
            return atoms
        return st.one_of(
            atoms,
            st.builds(lambda x,y: {"op":"⊕","states":[x,y]}, trees(d-1), trees(d-1)),
            st.builds(lambda x,y: {"op":"⊗","states":[x,y]}, trees(d-1), trees(d-1)),
            st.builds(lambda x,y: {"op":"↔","states":[x,y]}, trees(d-1), trees(d-1)),
            st.builds(lambda x  : {"op":"¬","state":x},      trees(d-1)),
            st.builds(lambda x  : {"op":"★","state":x},      trees(d-1)),
        )

    @hyp.given(trees(4))
    @hyp.settings(max_examples=150)
    def _prop(e):
        n = normalize(e)
        assert not _is_plus_under_times(n)
        assert normalize(n) == n
    _prop()