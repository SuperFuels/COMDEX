# File: backend/tests/test_symatics_rewriter.py
import math
import pytest

from backend.symatics import rewriter as R
from backend.symatics.terms import Sym, App

# ----------------
# Helpers
# ----------------
def A(): return Sym("A")
def B(): return Sym("B")
def C(): return Sym("C")
def bot(): return Sym("⊥")
def interf(phi, l, r): return App(Sym("⋈"), [Sym(str(R.norm_phase(phi))), l, r])

# ----------------
# Axiom Tests (Canonical)
# ----------------

def test_A1_comm_phi():
    """A ⋈[φ] B ↔ B ⋈[-φ] A (canonical ordering)."""
    expr = interf(1.0, B(), A())   # names swapped
    norm = R.normalize(expr)
    assert isinstance(norm, App)
    assert norm.head.name == "⋈"
    assert norm.args[1] == A() and norm.args[2] == B()
    assert norm.args[0].name == str(R.norm_phase(-1.0))

def test_A2_self_zero_id():
    """(A ⋈[0] A) ↔ A"""
    expr = interf(0.0, A(), A())
    norm = R.normalize(expr)
    assert norm == A()

def test_A3_self_pi_bot():
    """(A ⋈[π] A) ↔ ⊥"""
    expr = interf(math.pi, A(), A())
    norm = R.normalize(expr)
    assert norm == bot()

def test_A4_neutral_phi():
    """(A ⋈[φ] ⊥) ↔ A"""
    expr = interf(0.7, A(), bot())
    norm = R.normalize(expr)
    assert norm == A()

def test_A5_assoc_phase():
    """((A ⋈[φ] B) ⋈[ψ] C) ↔ (A ⋈[φ+ψ] (B ⋈[ψ] C))"""
    φ, ψ = 0.4, 0.8
    expr = interf(ψ, interf(φ, A(), B()), C())
    norm = R.normalize(expr)
    assert isinstance(norm, App)
    assert norm.head.name == "⋈"
    assert norm.args[1] == A()
    assert isinstance(norm.args[2], App)
    assert math.isclose(float(norm.args[0].name), R.norm_phase(φ + ψ))

def test_A6_inv_phase():
    """A ⋈[φ] (A ⋈[-φ] B) ↔ B"""
    φ = 0.9
    expr = interf(φ, A(), interf(-φ, A(), B()))
    norm = R.normalize(expr)
    assert norm == B()

def test_A7_fuse_phase_zero():
    """(A ⋈[0] B) ↔ (A ⊕ B)"""
    expr = interf(0.0, A(), B())
    norm = R.normalize(expr)
    assert isinstance(norm, App)
    assert norm.head.name == "⊕"
    assert norm.args == [A(), B()]

def test_A8_fuse_phase_pi():
    """(A ⋈[π] B) ↔ (A ⊖ B)"""
    expr = interf(math.pi, A(), B())
    norm = R.normalize(expr)
    assert isinstance(norm, App)
    assert norm.head.name == "⊖"
    assert norm.args == [A(), B()]

# ----------------
# Equivalence Tests
# ----------------

def test_structural_equiv_simple():
    assert R.symatics_structural_equiv(interf(0.0, A(), A()), A())

def test_truth_equiv_zero_phase():
    e1 = interf(0.0, A(), B())
    e2 = interf(0.0, A(), B())
    assert R.symatics_equiv(e1, e2)

def test_truth_equiv_nontrivial_phase():
    e1 = interf(0.2, A(), B())
    e2 = interf(0.2, A(), B())
    assert R.symatics_equiv(e1, e2)
    e3 = interf(-0.2, B(), A())
    assert not R.symatics_equiv(e1, e3)

# ----------------
# Regression Cases
# ----------------

def test_idempotence_cases():
    A_ = A()
    e0 = interf(0, A_, A_)
    assert R.normalize(e0) == A_

    epi = interf(math.pi, A_, A_)
    assert R.normalize(epi) == bot()

    ephi = interf(0.7, A_, A_)
    norm = R.normalize(ephi)
    assert norm != A_
    assert norm != bot()

def test_neutrality_and_comm():
    e = interf(1.23, A(), bot())
    assert R.normalize(e) == A()

    e1 = interf(0.5, A(), B())
    e2 = interf(-0.5, B(), A())
    assert R.symatics_structural_equiv(e1, e2)

def test_phase_addition_assoc():
    e = interf(0.3, interf(0.4, A(), B()), C())
    norm = R.normalize(e)
    expected = interf(0.7, A(), interf(0.3, B(), C()))
    assert norm == expected

# ----------------
# Canonical Bridge
# ----------------

def test_canonical_bridge_roundtrip():
    expr = App(Sym("⋈"), [Sym("0.0"), Sym("A"), Sym("B")])
    legacy = R.from_canonical(expr)
    back = R.to_canonical(legacy)
    assert isinstance(legacy, App)
    assert legacy.head.name == "⋈"
    assert isinstance(back, App)
    assert back.head.name == "⋈"

def test_canonical_equivalence_zero_phase():
    e = App(Sym("⋈"), [Sym("0.0"), Sym("A"), Sym("B")])
    legacy = R.from_canonical(e)
    norm = R.normalize(legacy)
    assert isinstance(norm, App)
    assert norm.head.name == "⊕"
    back = R.to_canonical(norm)
    assert isinstance(back, App)
    assert back.head.name == "⊕"