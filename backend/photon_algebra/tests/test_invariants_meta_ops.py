import pytest
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.core import (
    EMPTY, TOP, BOTTOM,
    similar, contains, superpose
)

def test_similarity_reflexive():
    # a ≈ a -> ⊤
    expr = similar("x", "x")
    assert normalize(expr) == TOP

def test_containment_bottom_left():
    # ⊥ ⊂ a -> ⊤
    expr = contains(BOTTOM, "y")
    assert normalize(expr) == TOP

def test_containment_top_right():
    # a ⊂ ⊤ -> ⊤
    expr = contains("z", TOP)
    assert normalize(expr) == TOP

def test_similarity_inert_for_different_terms():
    # a ≈ b (a != b) stays inert
    expr = similar("a", "b")
    out = normalize(expr)
    assert out.get("op") == "≈"
    assert out["states"] == ["a", "b"]

def test_containment_inert_for_nontrivial():
    # a ⊂ b (no shortcut) stays inert
    expr = contains("a", "b")
    out = normalize(expr)
    assert out.get("op") == "⊂"
    assert out["states"] == ["a", "b"]

def test_top_and_bottom_normalize_as_themselves():
    assert normalize(TOP) == TOP
    assert normalize(BOTTOM) == BOTTOM

def test_empty_normalizes_as_itself():
    assert normalize(EMPTY) == EMPTY

def test_superpose_with_empty_reduces():
    expr = superpose("a", EMPTY)
    assert normalize(expr) == "a"