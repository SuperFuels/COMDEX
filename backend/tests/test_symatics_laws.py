"""
Symatics ⋈ Laws Test Suite (v0.1)
---------------------------------
Smoke-test the interference axioms (A1-A8) via LAW_REGISTRY.
This ensures the registry wiring is correct, independent of Lean injection.
"""

import math
import pytest

from backend.symatics.symatics_rulebook import LAW_REGISTRY

# Simple test atoms
A = "A"
B = "B"
C = "C"


def test_comm_phi():
    law = LAW_REGISTRY["⋈"][0]  # comm_phi
    assert law(A, B, math.pi/4) is True
    assert law(A, B, 0) is True


def test_self_zero_and_self_pi():
    l_self_zero = LAW_REGISTRY["⋈"][1]  # self_zero
    l_self_pi   = LAW_REGISTRY["⋈"][2]  # self_pi

    assert l_self_zero(A) is True
    assert l_self_pi(A) is True


def test_non_idem():
    law = LAW_REGISTRY["⋈"][3]  # non_idem
    assert law(A, math.pi/4) is True   # nontrivial phase
    assert law(A, 0) is False          # fails for zero
    assert law(A, math.pi) is False    # fails for pi


def test_neutral_phi():
    law = LAW_REGISTRY["⋈"][4]  # neutral_phi
    assert law(A, 0.3) is True


def test_assoc_phase():
    law = LAW_REGISTRY["⋈"][5]  # assoc_phase
    assert law(A, B, C, 0.7, 1.1) is True


def test_inv_phase():
    law = LAW_REGISTRY["⋈"][6]  # inv_phase
    assert law(A, B, 1.23) is True