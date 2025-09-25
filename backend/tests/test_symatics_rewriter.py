import math
import pytest

from backend.modules.symatics import rewriter as R

# --------------
# Test Fixtures
# --------------

def A(): return R.Atom("A")
def B(): return R.Atom("B")
def C(): return R.Atom("C")
def bot(): return R.Bot()   # ✅ renamed from ⊥
def interf(phi, l, r): return R.Interf(R.norm_phase(phi), l, r)

# ----------------
# Axiom Tests
# ----------------

def test_A1_comm_phi():
    """A ⋈[φ] B ↔ B ⋈[-φ] A (canonical ordering)."""
    expr = interf(1.0, B(), A())   # names swapped
    norm = R.normalize(expr)
    assert isinstance(norm, R.Interf)
    assert norm.left == A() and norm.right == B()
    assert math.isclose(norm.phase, R.norm_phase(-1.0))

def test_A2_self_zero_id():
    """(A ⋈[0] A) ↔ A"""
    expr = interf(0.0, A(), A())
    norm = R.normalize(expr)
    assert norm == A()

def test_A3_self_pi_bot():
    """(A ⋈[π] A) ↔ ⊥"""
    expr = interf(math.pi, A(), A())
    norm = R.normalize(expr)
    assert isinstance(norm, R.Bot)

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
    assert isinstance(norm, R.Interf)
    assert norm.left == A()
    assert isinstance(norm.right, R.Interf)
    assert math.isclose(norm.phase, R.norm_phase(φ + ψ))

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
    assert isinstance(norm, R.SymAdd)
    assert norm.left == A() and norm.right == B()

def test_A8_fuse_phase_pi():
    """(A ⋈[π] B) ↔ (A ⊖ B)"""
    expr = interf(math.pi, A(), B())
    norm = R.normalize(expr)
    assert isinstance(norm, R.SymSub)
    assert norm.left == A() and norm.right == B()

# ----------------
# Equivalence Tests
# ----------------

def test_structural_equiv_simple():
    assert R.symatics_structural_equiv(interf(0.0, A(), A()), A())

def test_truth_equiv_zero_phase():
    """A ⋈[0] B structurally → SymAdd, but truth-style eqv holds only for φ=0/π"""
    e1 = interf(0.0, A(), B())
    e2 = interf(0.0, A(), B())
    assert R.symatics_equiv(e1, e2)

def test_truth_equiv_nontrivial_phase():
    """φ= arbitrary (not 0/π) requires exact structural equality."""
    e1 = interf(0.2, A(), B())
    e2 = interf(0.2, A(), B())
    assert R.symatics_equiv(e1, e2)
    e3 = interf(-0.2, B(), A())
    assert not R.symatics_equiv(e1, e3)