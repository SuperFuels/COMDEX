# backend/symatics/tests/test_rulebook_laws.py
import pytest
from backend.symatics import symatics_rulebook as SR

def test_law_commutativity_symbolic():
    assert SR.law_commutativity("⊕", "A", "B") is True
    assert SR.law_commutativity("↔", "ψ1", "ψ2") is True

def test_law_associativity_symbolic():
    assert SR.law_associativity("⊕", "A", "B", "C") is True

def test_law_resonance_stability_symbolic():
    expr = {"op": "ℚ", "args": ["ψ", 10], "result": "ψ·cos(ω₀t)·e^(-t/(2·10))"}
    assert SR.law_resonance_stability(expr) is True

def test_law_collapse_integrity_symbolic():
    expr = {"op": "μ", "collapsed": "ψ0"}
    assert SR.law_collapse_integrity(expr) is True

def test_law_projection_consistency_symbolic():
    expr = {"op": "π", "args": [[1, 2, 3], 1]}
    assert SR.law_projection_consistency(expr) is True