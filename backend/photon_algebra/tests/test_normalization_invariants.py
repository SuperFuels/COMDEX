# -*- coding: utf-8 -*-
import pytest
from backend.photon_algebra import rewriter

def has_plus_under_times(expr):
    """Check if ⊕ appears directly under ⊗."""
    if not isinstance(expr, dict):
        return False
    if expr.get("op") == "⊗":
        return any(isinstance(s, dict) and s.get("op") == "⊕" for s in expr.get("states", []))
    return any(has_plus_under_times(s) for s in expr.get("states", []) if isinstance(s, dict))

@pytest.mark.parametrize("expr,expected", [
    ({"op": "⊕", "states": ["a", {"op": "⊗", "states": ["a", "b"]}]}, "a"),
    ({"op": "⊗", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
     {"op": "⊕", "states": [
         {"op": "⊗", "states": ["a", "b"]},
         {"op": "⊗", "states": ["a", "c"]},
     ]}),
    ({"op": "¬", "state": {"op": "¬", "state": "a"}}, "a"),
    ({"op": "⊖", "states": ["a", {"op": "∅"}]}, "a"),
])
def test_core_invariants(expr, expected):
    norm = rewriter.normalize(expr)
    assert norm == expected

def test_no_plus_under_times_invariant():
    expr = {"op": "⊗", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]}
    norm = rewriter.normalize(expr)
    assert not has_plus_under_times(norm)

def test_idempotence_of_normalize():
    expr = {"op": "⊕", "states": ["a", {"op": "⊗", "states": ["a", "b"]}]}
    n1 = rewriter.normalize(expr)
    n2 = rewriter.normalize(n1)
    assert n1 == n2