# backend/photon_algebra/tests/test_axioms_phase1.py

import pytest
from backend.photon_algebra.core import (
    EMPTY, TOP, BOTTOM,
    identity, superpose, entangle, fuse, cancel, negate,
    collapse, project, to_boolean
)

# -----------------------
# P1 — Identity
# -----------------------
def test_identity():
    a = "a"
    assert identity(a) == a
    # identity should not alter non-empty states
    expr = superpose("a", "b")
    assert identity(expr) == expr

# -----------------------
# P2 — Superposition
# -----------------------
def test_superpose_basic():
    assert superpose() == EMPTY
    assert superpose("a") == {"op": "⊕", "states": ["a"]}
    expr = superpose("a", "b")
    assert expr["op"] == "⊕"
    assert set(expr["states"]) == {"a", "b"}

def test_superpose_flattening_via_rewrite():
    inner = superpose("a", "b")
    outer = superpose(inner, "c")
    # collapse should flatten
    flat = superpose("a", "b", "c")
    assert outer["op"] == "⊕"
    assert len(flat["states"]) == 3

# -----------------------
# P3 — Entanglement
# -----------------------
def test_entangle_symmetry():
    ab = entangle("a", "b")
    ba = entangle("b", "a")
    assert ab["op"] == "↔"
    assert set(ab["states"]) == set(ba["states"])

# -----------------------
# P4 — Fuse (⊗)
# -----------------------
def test_fuse_commutativity():
    ab = fuse("a", "b")
    ba = fuse("b", "a")
    assert ab["op"] == "⊗"
    assert set(ab["states"]) == set(ba["states"])

# -----------------------
# P5 — Cancel (⊖)
# -----------------------
def test_cancel_self_is_empty():
    assert cancel("a", "a") == EMPTY

def test_cancel_diff():
    expr = cancel("a", "b")
    assert expr["op"] == "⊖"
    assert expr["states"] == ["a", "b"]

# -----------------------
# P6 — Negate
# -----------------------
def test_negate_basic_and_double():
    n = negate("a")
    assert n == {"op": "¬", "state": "a"}
    # double negation collapses
    nn = negate(n)
    assert nn == "a"

# -----------------------
# P7 — Collapse (∇)
# -----------------------
def test_collapse_symbolic_and_weighted():
    expr = superpose("a", "b")
    symbolic = collapse(expr)
    assert symbolic["op"] == "∇"

    sqi = {"a": 1.0, "b": 0.0}
    chosen = collapse(expr, sqi)
    assert chosen == "a"

def test_collapse_non_superposition_is_noop():
    assert collapse("a") == "a"

# -----------------------
# P8 — Projection (★)
# -----------------------
def test_project_symbolic_and_weighted():
    symbolic = project("a")
    assert symbolic["op"] == "★"

    sqi = {"a": 0.75}
    weighted = project("a", sqi)
    assert weighted["op"] == "★"
    assert weighted["score"] == 0.75

# -----------------------
# Boolean subset
# -----------------------
def test_to_boolean_threshold():
    sqi = {"a": 0.8, "b": 0.2}
    assert to_boolean("a", sqi) == 1
    assert to_boolean("b", sqi) == 0