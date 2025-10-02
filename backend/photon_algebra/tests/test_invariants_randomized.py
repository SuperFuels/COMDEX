import pytest
from hypothesis import given, strategies as st

from backend.photon_algebra.rewriter import normalize, rewrite_fixed
from backend.photon_algebra.core import (
    EMPTY, TOP, BOTTOM,
    superpose, entangle, fuse, cancel, negate
)

# -------------------------
# Strategies
# -------------------------

atoms = st.sampled_from(["a", "b", "c", "x", "y", "z"])

@st.composite
def photon_exprs(draw, depth=0):
    """Generate recursive photon expressions for invariant tests."""
    if depth > 3:
        return draw(atoms)

    choice = draw(st.integers(min_value=0, max_value=6))
    if choice == 0:
        return draw(atoms)
    elif choice == 1:
        return superpose(draw(photon_exprs(depth=depth+1)), draw(photon_exprs(depth=depth+1)))
    elif choice == 2:
        return entangle(draw(photon_exprs(depth=depth+1)), draw(photon_exprs(depth=depth+1)))
    elif choice == 3:
        return fuse(draw(photon_exprs(depth=depth+1)), draw(photon_exprs(depth=depth+1)))
    elif choice == 4:
        return cancel(draw(photon_exprs(depth=depth+1)), draw(photon_exprs(depth=depth+1)))
    elif choice == 5:
        return negate(draw(photon_exprs(depth=depth+1)))
    else:
        return EMPTY

# -------------------------
# Invariant Tests
# -------------------------

@given(photon_exprs())
def test_normalize_idempotent(expr):
    assert normalize(normalize(expr)) == normalize(expr)

@given(photon_exprs())
def test_rewrite_fixed_idempotent(expr):
    lhs = rewrite_fixed(rewrite_fixed(expr))
    rhs = rewrite_fixed(expr)
    assert normalize(lhs) == normalize(rhs)

def test_superpose_identity():
    a = "a"
    expr = superpose(a, EMPTY)
    assert normalize(expr) == a

def test_double_negation():
    a = "x"
    expr = negate(negate(a))
    assert normalize(expr) == a

def test_absorption_rule():
    a, b = "p", "q"
    expr = superpose(a, fuse(a, b))
    assert normalize(expr) == normalize(a)

def test_distribution_rule():
    a, b, c = "u", "v", "w"
    left = fuse(a, superpose(b, c))
    right = superpose(fuse(a, b), fuse(a, c))
    assert normalize(left) == normalize(right)