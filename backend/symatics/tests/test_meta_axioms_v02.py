"""
Unit tests for Symatics Meta-Axioms v2.0
Ensures runtime validation and πₛ closure logic operate correctly.
"""

import pytest
import numpy as np
from backend.symatics.core.validators.pi_s_closure import validate_pi_s_closure
from backend.symatics.core.meta_axioms_v02 import META_AXIOMS


class DummyField:
    def __init__(self, phase):
        self.phase = phase


def test_meta_axioms_structure():
    """All meta-axioms should have required fields and unique IDs."""
    ids = [ax["id"] for ax in META_AXIOMS]
    assert len(ids) == len(set(ids)), "Duplicate Axiom IDs"
    for ax in META_AXIOMS:
        assert "statement" in ax
        assert "domain" in ax


def test_pi_s_closure_pass():
    """
    πₛ closure passes for coherent 2π n rotations.
    Allows small numerical drift due to finite sampling.
    """
    phi = np.linspace(0, 4 * np.pi, 1000)  # 2 full rotations
    result = validate_pi_s_closure(DummyField(phi))

    # Accept closure within 0.05 rad (~0.8% of 2π)
    tol = 0.05
    assert result["deviation"] < tol, f"Deviation {result['deviation']:.6f} exceeds tolerance {tol}"
    assert result["passed"], "Expected closure within tolerance"


def test_pi_s_closure_fail():
    """πₛ closure fails for non-integral phase rotations."""
    phi = np.linspace(0, 3.1 * np.pi, 1000)
    result = validate_pi_s_closure(DummyField(phi))
    assert not result["passed"], "Expected failure for incomplete rotation"