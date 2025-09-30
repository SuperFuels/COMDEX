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
    # recurse through tree
    if "states" in expr:
        return any(is_plus_under_times(s) for s in expr["states"])
    if "state" in expr:
        return is_plus_under_times(expr["state"])
    return False


# --- Edge cases --------------------------------------------------------------

def test_absorption_both_sides():
    a, b = "a", "b"
    expr1 = plus(a, times(a, b))      # a ⊕ (a ⊗ b) → a
    expr2 = plus(times(a, b), a)      # (a ⊗ b) ⊕ a → a
    assert normalize(expr1) == "a"
    assert normalize(expr2) == "a"

def test_annihilator_in_product():
    a = "a"
    assert normalize(times(a, EMPTY)) == EMPTY
    assert normalize(times(EMPTY, a)) == EMPTY

def test_idempotence_and_commutativity_in_sum():
    expr = {"op": "⊕", "states": ["b", "a", "a", "b"]}
    n = normalize(expr)
    # Should reduce to a canonical ordered sum with duplicates removed
    assert n == {"op": "⊕", "states": ["a", "b"]}

def test_dual_absorption_in_product():
    # a ⊗ (a ⊕ b) = a  and  (a ⊕ b) ⊗ a = a
    a, b = "x", "y"
    expr1 = times(a, plus(a, b))
    expr2 = times(plus(a, b), a)
    assert normalize(expr1) == "x"
    assert normalize(expr2) == "x"

def test_distribution_happens_only_from_times_branch():
    # (a ⊗ (b ⊕ c)) should distribute to (a⊗b) ⊕ (a⊗c)
    a, b, c = "a", "b", "c"
    expr = times(a, {"op": "⊕", "states": [b, c]})
    n = normalize(expr)
    assert n == {"op": "⊕", "states": [
        {"op": "⊗", "states": ["a", "b"]},
        {"op": "⊗", "states": ["a", "c"]},
    ]}
    # and no ⊕ appears directly under ⊗
    assert not is_plus_under_times(n)

def test_t14_cases_idempotent_and_terminate():
    # a ⊕ (b ⊗ c) and (b ⊗ c) ⊕ a should normalize without loops, then be idempotent
    a, b, c = "α", "β", "γ"
    expr1 = plus(a, times(b, c))
    expr2 = plus(times(b, c), a)
    n1 = normalize(expr1); n2 = normalize(n1)
    m1 = normalize(expr2); m2 = normalize(m1)
    assert n1 == n2
    assert m1 == m2
    assert not is_plus_under_times(n1)
    assert not is_plus_under_times(m1)


# --- Ordering / determinism --------------------------------------------------

def test_times_commutativity_canonical_order():
    # normalize should order product factors deterministically
    expr = times("z", "a")
    assert normalize(expr) == {"op": "⊗", "states": ["a", "z"]}

def test_plus_commutativity_canonical_order():
    # normalize should order sum terms deterministically and dedupe
    expr = {"op": "⊕", "states": ["z", "a", "m", "a"]}
    assert normalize(expr) == {"op": "⊕", "states": ["a", "m", "z"]}

def test_nested_mixed_ops_stability():
    # A slightly hairier tree just to ensure determinism and idempotence hold
    expr = plus(
        times("z", plus("a", "m")),
        plus(times("m", "z"), "a")
    )
    n1 = normalize(expr)
    n2 = normalize(n1)
    assert n1 == n2
    assert not is_plus_under_times(n1)

import pytest
from backend.photon_algebra.rewriter import normalize

def s(op, *args):
    if op == "⊕": return {"op":"⊕","states":[*args]}
    if op == "⊗": return {"op":"⊗","states":[*args]}
    if op == "∅": return {"op":"∅"}
    raise ValueError

def test_absorption_in_sum():
    # a ⊕ (a ⊗ b) → a
    expr = s("⊕", "a", s("⊗", "a", "b"))
    assert normalize(expr) == "a"

def test_dual_absorption_in_product_left():
    # (a ⊕ b) ⊗ a → a
    expr = s("⊗", s("⊕", "a", "b"), "a")
    assert normalize(expr) == "a"

def test_dual_absorption_in_product_right():
    # a ⊗ (a ⊕ b) → a
    expr = s("⊗", "a", s("⊕", "a", "b"))
    assert normalize(expr) == "a"

def test_commutativity_ordering_is_stable():
    expr = s("⊕", "b", "a", "c")
    n = normalize(expr)
    assert n["states"] == sorted(n["states"], key=lambda x: x if isinstance(x,str) else str(x))

def test_empty_annihilator_in_times():
    expr = s("⊗", "a", s("∅"))
    assert normalize(expr) == s("∅")

def test_times_distributes_over_plus():
    expr = s("⊗", "a", s("⊕", "b", "c"))
    n = normalize(expr)
    assert n["op"] == "⊕"
    assert {"op":"⊗","states":["a","b"]} in n["states"]
    assert {"op":"⊗","states":["a","c"]} in n["states"]