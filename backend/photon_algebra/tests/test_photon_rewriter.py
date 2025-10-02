# -*- coding: utf-8 -*-
"""
Unit tests for Photon Algebra Rewriter
--------------------------------------
Ensures core algebraic simplifications behave correctly:
    A ⊖ ∅ → A
    A ⊕ ∅ → A
    A ⊗ ∅ → ∅
    ¬∅   → ∅
"""

import pytest
from backend.photon_algebra import rewriter as PR
from backend.photon_algebra.core import EMPTY  # ✅ canonical ∅ dict


def normalize(expr):
    """Helper to run Photon normalize() cleanly."""
    return PR.normalize(expr)  # ✅ direct call


# ───────────────────────────────────────────────
# Identity Rules
# ───────────────────────────────────────────────
def test_subtraction_identity():
    assert normalize({"op": "⊖", "states": ["A", EMPTY]}) == "A"


def test_addition_identity():
    assert normalize({"op": "⊕", "states": ["A", EMPTY]}) == "A"


# ───────────────────────────────────────────────
# Absorbing Rules
# ───────────────────────────────────────────────
def test_tensor_absorbing():
    # A ⊗ ∅ → ∅
    assert normalize({"op": "⊗", "states": ["A", EMPTY]}) == EMPTY


def test_negation_empty():
    # ¬∅ → ∅
    assert normalize({"op": "¬", "state": EMPTY}) == EMPTY


# ───────────────────────────────────────────────
# Symmetry + Normalization
# ───────────────────────────────────────────────
def test_commutative_addition():
    """A ⊕ B = B ⊕ A"""
    lhs = normalize({"op": "⊕", "states": ["A", "B"]})
    rhs = normalize({"op": "⊕", "states": ["B", "A"]})
    assert lhs == rhs


def test_idempotent_addition():
    """A ⊕ A = A"""
    assert normalize({"op": "⊕", "states": ["A", "A"]}) == "A"


# ───────────────────────────────────────────────
# Nested Expressions
# ───────────────────────────────────────────────
def test_nested_subtraction_with_empty():
    """(A ⊖ ∅) ⊕ ∅ → A"""
    expr = {
        "op": "⊕",
        "states": [
            {"op": "⊖", "states": ["A", EMPTY]},
            EMPTY,
        ],
    }
    assert normalize(expr) == "A"