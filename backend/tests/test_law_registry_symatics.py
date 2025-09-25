"""
Law Registry Validation for ⋈[φ]
--------------------------------
Ensures LAW_REGISTRY["⋈"] entries are consistent with axioms
and rewriter-based theorems.
"""

import math
import pytest

import backend.symatics.rewriter as R
from backend.symatics.symatics_rulebook import LAW_REGISTRY

A = R.A()
B = R.B()
C = R.C()


def test_comm_phi_registry():
    law = LAW_REGISTRY["⋈"][0]  # comm_phi
    φ = 0.7
    lhs = R.interf(φ, A, B)
    rhs = R.interf(-φ, B, A)
    assert law(A, B, φ)
    assert R.symatics_structural_equiv(lhs, rhs)


def test_self_zero_registry():
    law = LAW_REGISTRY["⋈"][1]  # self_zero
    lhs = R.interf(0, A, A)
    rhs = A
    assert law(A)
    assert R.symatics_equiv(lhs, rhs)


def test_self_pi_registry():
    law = LAW_REGISTRY["⋈"][2]  # self_pi
    lhs = R.interf(math.pi, A, A)
    rhs = R.Bot()
    assert law(A)
    assert R.symatics_equiv(lhs, rhs)


def test_neutral_phi_registry():
    law = LAW_REGISTRY["⋈"][3]  # neutral_phi
    φ = 1.2
    lhs = R.interf(φ, A, R.Bot())
    rhs = A
    assert law(A, φ)
    assert R.symatics_equiv(lhs, rhs)


def test_assoc_phase_registry():
    law = LAW_REGISTRY["⋈"][4]  # assoc_phase
    φ, ψ = 0.7, 1.1
    lhs = R.interf(ψ, R.interf(φ, A, B), C)
    rhs = R.interf(φ + ψ, A, R.interf(ψ, B, C))
    assert law(A, B, C, φ, ψ)
    assert R.symatics_structural_equiv(lhs, rhs)


def test_inv_phase_registry():
    law = LAW_REGISTRY["⋈"][5]  # inv_phase
    φ = 0.9
    lhs = R.interf(φ, A, R.interf(-φ, A, B))
    rhs = B
    assert law(A, B, φ)
    assert R.symatics_equiv(lhs, rhs)