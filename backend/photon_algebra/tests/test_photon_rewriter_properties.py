# File: backend/photon_algebra/tests/test_photon_rewriter_properties.py
import pytest
from backend.photon_algebra import rewriter as PR
from backend.photon_algebra.core import TOP, BOTTOM, EMPTY
import hypothesis.strategies as st
from hypothesis import given

# Helpers
def normalize(expr):
    return PR.normalize(expr)

def render(expr):
    from backend.photon_algebra.renderer import render_photon
    return render_photon(normalize(expr))

# Strategy: generate random photon expressions
def photon_exprs(max_depth=3):
    if max_depth <= 0:
        # Atoms: variable symbols or ∅, ⊤, ⊥
        return st.sampled_from(["x", "y", "z", {"op": "∅"}, {"op": "⊤"}, {"op": "⊥"}])

    return st.deferred(
        lambda: st.one_of(
            # atomic
            st.sampled_from(["x", "y", "z", {"op": "∅"}, {"op": "⊤"}, {"op": "⊥"}]),
            # unary ops
            st.builds(lambda e: {"op": "¬", "state": e}, photon_exprs(max_depth - 1)),
            st.builds(lambda e: {"op": "★", "state": e}, photon_exprs(max_depth - 1)),
            # binary/ternary ops
            st.builds(lambda a, b: {"op": "⊕", "states": [a, b]},
                      photon_exprs(max_depth - 1), photon_exprs(max_depth - 1)),
            st.builds(lambda a, b: {"op": "⊗", "states": [a, b]},
                      photon_exprs(max_depth - 1), photon_exprs(max_depth - 1)),
            st.builds(lambda a, b: {"op": "↔", "states": [a, b]},
                      photon_exprs(max_depth - 1), photon_exprs(max_depth - 1)),
            st.builds(lambda a, b: {"op": "≈", "states": [a, b]},
                      photon_exprs(max_depth - 1), photon_exprs(max_depth - 1)),
            st.builds(lambda a, b: {"op": "⊂", "states": [a, b]},
                      photon_exprs(max_depth - 1), photon_exprs(max_depth - 1)),
        )
    )

@given(photon_exprs())
def test_normalize_idempotent(expr):
    # Normalization should be idempotent: normalize(normalize(expr)) == normalize(expr)
    n1 = normalize(expr)
    n2 = normalize(n1)
    assert n1 == n2

def test_duality_negation():
    # a ⊕ ¬a -> ⊤
    expr = {"op": "⊕", "states": ["x", {"op": "¬", "state": "x"}]}
    norm = normalize(expr)
    assert norm == TOP or render(norm) == "⊤"

def test_distribution_tensor_over_plus():
    # a ⊗ (b ⊕ c) -> (a ⊗ b) ⊕ (a ⊗ c)
    expr = {"op": "⊗", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]}
    norm = normalize(expr)
    rendered = render(norm)
    assert rendered in ("((a ⊗ b) ⊕ (a ⊗ c))", "((a ⊗ c) ⊕ (a ⊗ b))")

def test_de_morgan_or_to_and():
    # ¬(a ⊕ b) -> (¬a ⊗ ¬b)
    expr = {"op": "¬", "state": {"op": "⊕", "states": ["a", "b"]}}
    norm = normalize(expr)
    assert render(norm) in ("(¬a ⊗ ¬b)", "(¬b ⊗ ¬a)")

def test_de_morgan_and_to_or():
    # ¬(a ⊗ b) -> (¬a ⊕ ¬b)
    expr = {"op": "¬", "state": {"op": "⊗", "states": ["a", "b"]}}
    norm = normalize(expr)
    assert render(norm) in ("(¬a ⊕ ¬b)", "(¬b ⊕ ¬a)")
# -----------------------------------------------------------------------------
# Canonical laws of Photon algebra
# -----------------------------------------------------------------------------

def test_idempotence_superpose():
    # a ⊕ a -> a
    expr = {"op": "⊕", "states": ["a", "a"]}
    norm = normalize(expr)
    assert render(norm) == "a"

def test_absorption_negation():
    # a ⊗ ¬a -> ⊥
    expr = {"op": "⊗", "states": ["a", {"op": "¬", "state": "a"}]}
    norm = normalize(expr)
    assert norm == {"op": "⊥"} or render(norm) == "⊥"

def test_absorption_superpose():
    # a ⊕ (a ⊗ b) -> a
    expr = {"op": "⊕", "states": ["a", {"op": "⊗", "states": ["a", "b"]}]}
    norm = normalize(expr)
    assert render(norm) == "a"

def test_double_negation():
    # ¬(¬a) -> a
    expr = {"op": "¬", "state": {"op": "¬", "state": "x"}}
    norm = normalize(expr)
    assert render(norm) == "x"

def test_empty_identity():
    # a ⊕ ∅ -> a
    expr = {"op": "⊕", "states": ["p", {"op": "∅"}]}
    norm = normalize(expr)
    assert render(norm) == "p"

def test_bottom_subset_any():
    # ⊥ ⊂ x -> ⊤
    expr = {"op": "⊂", "states": [{"op": "⊥"}, "z"]}
    norm = normalize(expr)
    assert norm == {"op": "⊤"} or render(norm) == "⊤"

def test_similarity_reflexive():
    # x ≈ x -> ⊤
    expr = {"op": "≈", "states": ["x", "x"]}
    norm = normalize(expr)
    assert norm == {"op": "⊤"} or render(norm) == "⊤"

def test_projection_distribution():
    # ★(a↔b) -> (★a ⊕ ★b)
    expr = {"op": "★", "state": {"op": "↔", "states": ["m", "n"]}}
    norm = normalize(expr)
    r = render(norm)
    assert "★m" in r and "★n" in r and "⊕" in r

import random
import string
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.renderer import render_photon


def test_associativity_flattening_plus():
    # a ⊕ (b ⊕ a) -> a ⊕ b
    expr = {"op": "⊕", "states": ["a", {"op": "⊕", "states": ["b", "a"]}]}
    norm = normalize(expr)
    rendered = render_photon(norm)
    assert rendered in ("(a ⊕ b)", "(b ⊕ a)")


def test_associativity_flattening_tensor():
    # a ⊗ (b ⊗ a) -> a ⊗ b
    expr = {"op": "⊗", "states": ["a", {"op": "⊗", "states": ["b", "a"]}]}
    norm = normalize(expr)
    rendered = render_photon(norm)
    assert rendered in ("(a ⊗ b)", "(b ⊗ a)")


def test_distributivity_tensor_over_plus_left():
    # a ⊗ (b ⊕ c) -> (a ⊗ b) ⊕ (a ⊗ c)
    expr = {"op": "⊗", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]}
    norm = normalize(expr)
    rendered = render_photon(norm)
    assert "(a ⊗ b)" in rendered and "(a ⊗ c)" in rendered


def test_distributivity_tensor_over_plus_right():
    # (a ⊕ b) ⊗ c -> (a ⊗ c) ⊕ (b ⊗ c)
    expr = {"op": "⊗", "states": [{"op": "⊕", "states": ["a", "b"]}, "c"]}
    norm = normalize(expr)
    rendered = render_photon(norm)
    assert "(a ⊗ c)" in rendered and "(b ⊗ c)" in rendered


def random_expr(depth=2):
    """Generate a random photon expression with limited depth."""
    atoms = list(string.ascii_lowercase[:5])  # a-e
    if depth == 0:
        return random.choice(atoms)

    ops = ["⊕", "⊗", "¬", "⊖"]
    op = random.choice(ops)

    if op == "¬":
        return {"op": "¬", "state": random_expr(depth - 1)}
    elif op in {"⊕", "⊗", "⊖"}:
        return {"op": op, "states": [random_expr(depth - 1), random_expr(depth - 1)]}
    else:
        return random.choice(atoms)


def test_random_expression_idempotence():
    # Stress test: normalize twice should equal normalize once
    for _ in range(20):
        expr = random_expr(depth=3)
        n1 = normalize(expr)
        n2 = normalize(n1)
        assert n1 == n2
        assert render_photon(n1) == render_photon(n2)