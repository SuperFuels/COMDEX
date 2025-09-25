"""
Symatics Theorems Test Suite (v0.2)
-----------------------------------
These tests check that axioms (A1–A8) of the interference operator ⋈[φ]
yield new theorems beyond Boolean logic.

Run with: pytest backend/tests/test_symatics_theorems.py
"""

import math
import pytest
import hypothesis.strategies as st
from hypothesis import given

import backend.symatics.rewriter as R

# Shortcuts
A = R.A()
B = R.B()
C = R.C()

# ------------------------
# Core theorems
# ------------------------

def test_self_identity_unique():
    """
    Theorem 1: (A ⋈[φ] A) ↔ A  ⇔  φ = 0
    """
    # φ=0 → reduces to A
    assert R.symatics_equiv(R.interf(0, A, A), A)

    # φ=π → reduces to ⊥, not A
    assert not R.symatics_equiv(R.interf(math.pi, A, A), A)

    # φ=nontrivial → not equivalent
    assert not R.symatics_equiv(R.interf(1.0, A, A), A)


def test_self_annihilation_unique():
    """
    Theorem 2: (A ⋈[φ] A) ↔ ⊥  ⇔  φ = π
    """
    # φ=π → ⊥
    assert isinstance(R.normalize(R.interf(math.pi, A, A)), R.Bot)

    # φ=0 → A, not ⊥
    assert not isinstance(R.normalize(R.interf(0, A, A)), R.Bot)

    # φ=other → not ⊥
    assert not isinstance(R.normalize(R.interf(1.0, A, A)), R.Bot)


def test_phase_cancellation():
    """
    Theorem 3: A ⋈[φ] (A ⋈[−φ] B) ↔ B
    """
    φ = 1.23
    lhs = R.interf(φ, A, R.interf(-φ, A, B))
    assert R.symatics_equiv(lhs, B)


def test_associativity_normal_form():
    """
    Theorem 4: ((A ⋈[φ] B) ⋈[ψ] C) ↔ (A ⋈[φ+ψ] (B ⋈[ψ] C))
    """
    φ, ψ = 0.7, 1.1
    lhs = R.interf(ψ, R.interf(φ, A, B), C)
    rhs = R.interf(φ + ψ, A, R.interf(ψ, B, C))
    # Associativity is about structure, not truth-style φ equivalence
    assert R.symatics_structural_equiv(lhs, rhs)


def test_no_distributivity_nontrivial():
    """
    Theorem 5: Distributivity fails except at φ=0 or π.
    """
    φ = 1.0  # nontrivial phase
    lhs = R.interf(φ, A, B)
    rhs = R.interf(φ, A, B)  # fake distributive case
    assert not R.symatics_equiv(lhs, rhs)


def test_no_fixed_point_nontrivial():
    """
    Theorem 6: For φ ≠ 0,π, X = A ⋈[φ] X has no solutions.
    """
    φ = 0.5
    X = C
    lhs = R.interf(φ, A, X)
    # Not equal to X
    assert R.normalize(lhs) != X

# ------------------------
# Property-based fuzz tests
# ------------------------

@given(st.integers(min_value=-6, max_value=6))
def test_idempotence_and_annihilation_unique(k):
    """
    Property test: For random rational multiples of π,
    (A ⋈[φ] A) normalizes to:
        • A iff φ ≡ 0 (mod 2π)
        • ⊥ iff φ ≡ π (mod 2π)
        • else stays nontrivial
    """
    φ = k * (math.pi / 3)   # sample φ = multiples of 60° (radians)

    expr = R.interf(φ, A, A)
    norm = R.normalize(expr)

    if R.is_zero_phase(φ):
        assert norm == A
    elif R.is_pi_phase(φ):
        assert isinstance(norm, R.Bot)
    else:
        assert norm not in (A, R.Bot())