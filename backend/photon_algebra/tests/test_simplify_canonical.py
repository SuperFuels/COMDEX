# -*- coding: utf-8 -*-
"""
Tests: Photon Canonical Simplifier
==================================
Verifies algebraic normalization (commutativity, identity, idempotency, flattening)
for Photon Algebra IR via simplify_canonical.canonicalize().
"""

import json
from backend.photon_algebra.simplify_canonical import canonicalize


# -------------------------------------------------------------------------
# 1. Commutativity and determinism
# -------------------------------------------------------------------------
def test_commutativity():
    expr1 = {"op": "⊕", "states": ["a", "b"]}
    expr2 = {"op": "⊕", "states": ["b", "a"]}
    assert canonicalize(expr1) == canonicalize(expr2)

    expr3 = {"op": "⊗", "states": ["x", "y"]}
    expr4 = {"op": "⊗", "states": ["y", "x"]}
    assert canonicalize(expr3) == canonicalize(expr4)


# -------------------------------------------------------------------------
# 2. Idempotency
# -------------------------------------------------------------------------
def test_idempotent_simplify():
    expr = {"op": "⊕", "states": ["a", "a", "a"]}
    result = canonicalize(expr)
    assert result == "a" or result == {"op": "⊕", "states": ["a"]}

    expr2 = {"op": "⊗", "states": ["b", "b"]}
    result2 = canonicalize(expr2)
    assert result2 == "b" or result2 == {"op": "⊗", "states": ["b"]}


# -------------------------------------------------------------------------
# 3. Flattening nested same-op
# -------------------------------------------------------------------------
def test_flattening():
    expr = {
        "op": "⊕",
        "states": [
            "a",
            {"op": "⊕", "states": ["b", "c"]},
            {"op": "⊕", "states": ["d", "a"]},
        ],
    }
    result = canonicalize(expr)
    flat_states = result["states"] if isinstance(result, dict) else [result]
    assert all(isinstance(s, str) for s in flat_states)
    assert set(flat_states) == {"a", "b", "c", "d"}


# -------------------------------------------------------------------------
# 4. Identity elimination
# -------------------------------------------------------------------------
def test_identity_rules():
    # OR with ∅ and ⊥ should drop them
    expr = {"op": "⊕", "states": [{"op": "∅"}, {"op": "⊥"}, "x"]}
    assert canonicalize(expr) == "x"

    # AND with ⊤ should drop it
    expr2 = {"op": "⊗", "states": [{"op": "⊤"}, "y"]}
    assert canonicalize(expr2) == "y"

    # OR with ⊤ dominates
    expr3 = {"op": "⊕", "states": ["z", {"op": "⊤"}]}
    assert canonicalize(expr3) == {"op": "⊤"}

    # AND with ⊥ dominates
    expr4 = {"op": "⊗", "states": ["z", {"op": "⊥"}]}
    assert canonicalize(expr4) == {"op": "⊥"}


# -------------------------------------------------------------------------
# 5. Nested mixed ops are preserved
# -------------------------------------------------------------------------
def test_nested_ops_preserved():
    expr = {"op": "⊕", "states": [{"op": "⊗", "states": ["a", "b"]}, "c"]}
    result = canonicalize(expr)
    assert result["op"] == "⊕"
    assert any(_["op"] == "⊗" for _ in result["states"] if isinstance(_, dict))


# -------------------------------------------------------------------------
# 6. Complex flatten + idempotent + identity combined
# -------------------------------------------------------------------------
def test_complex_canonicalization():
    expr = {
        "op": "⊕",
        "states": [
            {"op": "⊕", "states": ["a", "b", "a"]},
            {"op": "∅"},
            {"op": "⊥"},
            {"op": "⊗", "states": ["x", {"op": "⊤"}]},
        ],
    }
    result = canonicalize(expr)
    expected_flat = {"op": "⊕", "states": ["a", "b", "x"]}
    expected_nested = {"op": "⊕", "states": ["a", "b", {"op": "⊗", "states": ["x"]}]}
    assert result == expected_flat or result == expected_nested


# -------------------------------------------------------------------------
# Optional smoke test for manual run
# -------------------------------------------------------------------------
if __name__ == "__main__":
    expr = {
        "op": "⊕",
        "states": [
            {"op": "⊗", "states": [{"op": "⊤"}, "a"]},
            {"op": "⊕", "states": ["b", "a", {"op": "∅"}]},
            {"op": "⊕", "states": ["a", "b"]},
        ],
    }
    print("Before:\n", json.dumps(expr, ensure_ascii=False, indent=2))
    print("After:\n", json.dumps(canonicalize(expr), ensure_ascii=False, indent=2))