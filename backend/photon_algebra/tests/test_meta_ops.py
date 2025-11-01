# backend/photon_algebra/tests/test_meta_ops.py

import pytest
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.core import TOP, BOTTOM, EMPTY

def test_similarity_reflexive():
    """a ≈ a -> ⊤"""
    expr = {"op": "≈", "states": ["x", "x"]}
    assert normalize(expr) == TOP

def test_similarity_nonreflexive_inert():
    """a ≈ b stays inert if a != b"""
    expr = {"op": "≈", "states": ["a", "b"]}
    result = normalize(expr)
    assert result["op"] == "≈"
    assert result["states"] == ["a", "b"]

def test_containment_bottom_left():
    """⊥ ⊂ a -> ⊤"""
    expr = {"op": "⊂", "states": [BOTTOM, "a"]}
    assert normalize(expr) == TOP

def test_containment_top_right():
    """a ⊂ ⊤ -> ⊤"""
    expr = {"op": "⊂", "states": ["a", TOP]}
    assert normalize(expr) == TOP

def test_containment_nontrivial_inert():
    """a ⊂ b stays inert unless shortcut applies"""
    expr = {"op": "⊂", "states": ["a", "b"]}
    result = normalize(expr)
    assert result["op"] == "⊂"
    assert result["states"] == ["a", "b"]

def test_constants_pass_through():
    """⊤, ⊥, ∅ normalize to themselves"""
    assert normalize(TOP) == TOP
    assert normalize(BOTTOM) == BOTTOM
    assert normalize(EMPTY) == EMPTY

def test_nested_similarity_stability():
    """Nested similarity stays inert if not reflexive"""
    expr = {"op": "≈", "states": ["a", {"op": "⊕", "states": ["a", "b"]}]}
    result = normalize(expr)
    assert result["op"] == "≈"

def test_nested_containment_bottom_top():
    """⊥ ⊂ ⊤ -> ⊤"""
    expr = {"op": "⊂", "states": [BOTTOM, TOP]}
    assert normalize(expr) == TOP