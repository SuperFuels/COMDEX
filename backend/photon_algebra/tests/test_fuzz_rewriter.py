# -*- coding: utf-8 -*-
# File: backend/photon_algebra/tests/test_fuzz_rewriter.py

import json
from hypothesis import given, strategies as st, settings, HealthCheck
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.core import EMPTY  # 🔑 shared canonical empty

# ---------------------------
# Generators
# ---------------------------

# Simple leaf symbols (you can expand later)
leaf = st.sampled_from(list("abcdefghijklmnopqrstuvwxyz"))

def expr_strategy(max_depth: int = 4):
    """Random Photon expressions with bounded depth."""
    if max_depth <= 0:
        return leaf

    # Build recursively
    return st.deferred(lambda: st.one_of(
        # Leaf
        leaf,
        # Unary: ¬
        st.builds(lambda s: {"op": "¬", "state": s}, expr_strategy(max_depth - 1)),
        # Binary ops with fixed arity = 2
        st.builds(lambda a, b: {"op": "⊗", "states": [a, b]},
                  expr_strategy(max_depth - 1), expr_strategy(max_depth - 1)),
        st.builds(lambda a, b: {"op": "⊖", "states": [a, b]},
                  expr_strategy(max_depth - 1), expr_strategy(max_depth - 1)),
        st.builds(lambda a, b: {"op": "↔", "states": [a, b]},
                  expr_strategy(max_depth - 1), expr_strategy(max_depth - 1)),
        # N-ary ⊕ (1..4 terms) to exercise flatten/sort/dedupe paths
        st.builds(lambda xs: {"op": "⊕", "states": xs},
                  st.lists(expr_strategy(max_depth - 1), min_size=1, max_size=4)),
    ))

rand_expr = expr_strategy(4)

# Aggressive default; can down-tune in CI by HYPOTHESIS_MAX_EXAMPLES env var
DEF_SETTINGS = dict(
    max_examples=1000,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

# ---------------------------
# Invariants & Identities
# ---------------------------

@given(expr=rand_expr)
@settings(**DEF_SETTINGS)
def test_normalize_idempotent(expr):
    """normalize(normalize(x)) == normalize(x)"""
    n1 = normalize(expr)
    n2 = normalize(n1)
    assert n1 == n2

@given(expr=rand_expr)
@settings(**DEF_SETTINGS)
def test_normalize_is_deterministic_string(expr):
    """String form of normalized expr is stable across runs."""
    n = normalize(expr)
    s1 = json.dumps(n, sort_keys=True, ensure_ascii=False)
    s2 = json.dumps(normalize(expr), sort_keys=True, ensure_ascii=False)
    assert s1 == s2

@given(a=leaf, b=leaf)
@settings(**DEF_SETTINGS)
def test_commutativity_sample(a, b):
    """a ⊕ b ≡ b ⊕ a (after normalize)"""
    e1 = {"op": "⊕", "states": [a, b]}
    e2 = {"op": "⊕", "states": [b, a]}
    assert normalize(e1) == normalize(e2)

@given(a=leaf, b=leaf, c=leaf)
@settings(**DEF_SETTINGS)
def test_associativity_sample(a, b, c):
    """(a ⊕ b) ⊕ c ≡ a ⊕ (b ⊕ c)"""
    e1 = {"op": "⊕", "states": [ {"op": "⊕", "states": [a, b]}, c ]}
    e2 = {"op": "⊕", "states": [ a, {"op": "⊕", "states": [b, c]} ]}
    assert normalize(e1) == normalize(e2)

@given(a=leaf, b=leaf, c=leaf)
@settings(**DEF_SETTINGS)
def test_distributivity_sample(a, b, c):
    """a ⊗ (b ⊕ c) ≡ (a ⊗ b) ⊕ (a ⊗ c)"""
    left = {"op": "⊗", "states": [a, {"op": "⊕", "states": [b, c]}]}
    right = {"op": "⊕", "states": [
        {"op": "⊗", "states": [a, b]},
        {"op": "⊗", "states": [a, c]},
    ]}
    assert normalize(left) == normalize(right)

@given(a=leaf)
@settings(**DEF_SETTINGS)
def test_idempotence_sample(a):
    """a ⊕ a ≡ a"""
    e = {"op": "⊕", "states": [a, a]}
    assert normalize(e) == a

@given(a=leaf)
@settings(**DEF_SETTINGS)
def test_cancellation_sample(a):
    """a ⊖ a ≡ ∅"""
    e = {"op": "⊖", "states": [a, a]}
    assert normalize(e) == EMPTY  # 🔑 use shared constant

@given(a=leaf)
@settings(**DEF_SETTINGS)
def test_double_negation_sample(a):
    """¬(¬a) ≡ a"""
    e = {"op": "¬", "state": {"op": "¬", "state": a}}
    assert normalize(e) == a