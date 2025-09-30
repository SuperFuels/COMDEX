# backend/photon_algebra/tests/test_edges_and_ordering.py
import pytest
from backend.photon_algebra.rewriter import normalize

EMPTY = {"op": "∅"}

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
    if "states" in expr:
        return any(is_plus_under_times(s) for s in expr["states"])
    if "state" in expr:
        return is_plus_under_times(expr["state"])
    return False


# --- Edge cases --------------------------------------------------------------

def test_annihilator_in_times():
    assert normalize(times("a", EMPTY)) == EMPTY
    assert normalize(times(EMPTY, "a")) == EMPTY

def test_dual_absorption_times_over_plus():
    # a ⊗ (a ⊕ b) → a
    assert normalize(times("a", plus("a", "b"))) == "a"
    # (a ⊕ b) ⊗ a → a
    assert normalize(times(plus("a", "b"), "a")) == "a"

def test_plus_absorption_against_product():
    # a ⊕ (a ⊗ b) → a
    assert normalize(plus("a", times("a", "b"))) == "a"
    # (a ⊗ b) ⊕ a → a
    assert normalize(plus(times("a", "b"), "a")) == "a"

def test_distribution_happens_only_from_times_branch():
    # a ⊗ (b ⊕ c) → (a⊗b) ⊕ (a⊗c)
    a, b, c = "a", "b", "c"
    n = normalize(times(a, {"op": "⊕", "states": [b, c]}))
    assert n == {
        "op": "⊕",
        "states": [
            {"op": "⊗", "states": ["a", "b"]},
            {"op": "⊗", "states": ["a", "c"]},
        ],
    }
    assert not is_plus_under_times(n)

def test_t14_forms_terminate_and_are_idempotent():
    # a ⊕ (b ⊗ c)   and   (b ⊗ c) ⊕ a
    a, b, c = "α", "β", "γ"
    e1 = plus(a, times(b, c))
    e2 = plus(times(b, c), a)

    n1 = normalize(e1)
    m1 = normalize(e2)
    # idempotence
    assert normalize(n1) == n1
    assert normalize(m1) == m1
    # invariant
    assert not is_plus_under_times(n1)
    assert not is_plus_under_times(m1)


# --- Ordering / determinism --------------------------------------------------

def test_times_commutativity_canonical_order():
    assert normalize(times("z", "a")) == {"op": "⊗", "states": ["a", "z"]}

def test_plus_commutativity_and_dedup():
    n = normalize({"op": "⊕", "states": ["z", "a", "m", "a"]})
    assert n == {"op": "⊕", "states": ["a", "m", "z"]}

def test_nested_mixed_ops_stability():
    expr = plus(
        times("z", plus("a", "m")),
        plus(times("m", "z"), "a"),
    )
    n1 = normalize(expr)
    n2 = normalize(n1)
    assert n1 == n2
    assert not is_plus_under_times(n1)

def test_no_plus_under_times_invariant_and_idempotence():
    expr = times(plus("a", "b"), plus("c", "d"))
    n = normalize(expr)
    assert not is_plus_under_times(n)
    assert normalize(n) == n