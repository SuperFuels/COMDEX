# backend/tests/test_operator_fuse.py
import math
import pytest

from backend.symatics.signature import Signature
from backend.symatics.operators import apply_operator


def make_sig(A=1.0, f=1.0, phi=0.0, pol="H"):
    """Helper to create simple test signatures."""
    return Signature(
        amplitude=A,
        frequency=f,
        phase=phi,
        polarization=pol,
        mode=None,
        oam_l=None,
        envelope=None,
        meta={"src": "test"},
    )


# -----------------------------------------------------------------------------
# Metadata + Bookkeeping
# -----------------------------------------------------------------------------

def test_fuse_metadata_and_op_tag():
    """
    Fused signatures must carry metadata:
    - operator tag ("⋈")
    - explicit phi if provided
    """
    s1 = make_sig(A=1.0, f=1.0, phi=0.0)
    s2 = make_sig(A=1.0, f=1.0, phi=math.pi / 2)

    out = apply_operator("⋈", s1, s2, phi=0.5)

    assert isinstance(out, Signature)
    assert out.meta["op"] == "⋈"
    assert math.isclose(out.meta["phi"], 0.5, abs_tol=1e-12)


# -----------------------------------------------------------------------------
# Intrinsic phase cancellation (no explicit φ)
# -----------------------------------------------------------------------------

def test_fuse_destructive_interference_intrinsic():
    """Intrinsic phase difference = π -> destructive interference."""
    s1 = make_sig(A=1.0, f=2.0, phi=0.0)
    s2 = make_sig(A=1.0, f=2.0, phi=math.pi)

    out = apply_operator("⋈", s1, s2)  # no φ passed

    assert out.amplitude == pytest.approx(0.0, abs=1e-6)
    assert out.frequency == pytest.approx(2.0)
    assert out.polarization == "H"  # stable bias


def test_fuse_constructive_interference_intrinsic():
    """Intrinsic phase alignment -> constructive interference (doubling)."""
    s1 = make_sig(A=1.0, f=2.0, phi=0.0)
    s2 = make_sig(A=1.0, f=2.0, phi=0.0)

    out = apply_operator("⋈", s1, s2)

    assert out.amplitude == pytest.approx(2.0, rel=1e-6)
    assert out.phase == pytest.approx(0.0, abs=1e-6)
    assert out.frequency == pytest.approx(2.0)
    assert out.polarization == "H"


# -----------------------------------------------------------------------------
# Explicit φ offset interference
# -----------------------------------------------------------------------------

def test_fuse_destructive_interference_explicit_phi():
    """Explicit φ = π -> destructive interference, amplitudes cancel."""
    s1 = make_sig(A=1.0, f=2.0, phi=0.0)
    s2 = make_sig(A=1.0, f=2.0, phi=0.0)

    out = apply_operator("⋈", s1, s2, phi=math.pi)

    assert out.amplitude == pytest.approx(0.0, abs=1e-6)
    assert math.isclose(out.meta["phi"], math.pi, abs_tol=1e-12)


def test_fuse_constructive_interference_explicit_phi():
    """Explicit φ = 0 -> constructive interference, amplitudes add."""
    s1 = make_sig(A=1.0, f=2.0, phi=0.0)
    s2 = make_sig(A=1.0, f=2.0, phi=0.0)

    out = apply_operator("⋈", s1, s2, phi=0.0)

    assert out.amplitude == pytest.approx(2.0, rel=1e-6)
    assert math.isclose(out.meta["phi"], 0.0, abs_tol=1e-12)

# ---------------------------------------------------------------------------
# A7 & A8 correspondence tests (Lean ↔ Python semantics)
# ---------------------------------------------------------------------------

def test_axiom_A7_constructive_zero_phase():
    """A7: (A ⋈[0] B) ↔ (A ⊕ B)"""
    s1 = make_sig(A=1.0, f=2.0, phi=0.0)
    s2 = make_sig(A=1.0, f=2.0, phi=0.0)

    fuse_out = apply_operator("⋈", s1, s2, phi=0.0)
    superpose_out = apply_operator("⊕", s1, s2)

    assert fuse_out.amplitude == pytest.approx(superpose_out.amplitude, rel=1e-6)
    assert fuse_out.phase == pytest.approx(superpose_out.phase, abs=1e-6)
    assert fuse_out.frequency == pytest.approx(superpose_out.frequency, rel=1e-9)


def test_axiom_A8_destructive_pi_phase():
    """A8: (A ⋈[π] B) ↔ (A ⊖ B)"""
    s1 = make_sig(A=1.0, f=2.0, phi=0.0)
    s2 = make_sig(A=1.0, f=2.0, phi=0.0)

    fuse_out = apply_operator("⋈", s1, s2, phi=math.pi)
    cancel_out = apply_operator("⊖", s1, s2)

    assert fuse_out.amplitude == pytest.approx(cancel_out.amplitude, abs=1e-6)
    assert fuse_out.phase == pytest.approx(cancel_out.phase, abs=1e-6)
    assert fuse_out.frequency == pytest.approx(cancel_out.frequency, rel=1e-9)

def test_axiom_A8_destructive_pi_phase():
    """A8: (A ⋈[π] B) ↔ (A ⊖ B)"""
    s1 = make_sig(A=1.0, f=2.0, phi=0.0)
    s2 = make_sig(A=1.0, f=2.0, phi=0.0)

    fuse_out = apply_operator("⋈", s1, s2, phi=math.pi)
    cancel_out = apply_operator("⊖", s1, s2)

    # Amplitudes must agree
    assert fuse_out.amplitude == pytest.approx(cancel_out.amplitude, abs=1e-6)

    # If amplitude ~ 0, phase is undefined -> skip phase check
    if abs(fuse_out.amplitude) > 1e-9:
        assert fuse_out.phase == pytest.approx(cancel_out.phase, abs=1e-6)

    # Frequency and polarization should still agree
    assert fuse_out.frequency == pytest.approx(cancel_out.frequency)
    assert fuse_out.polarization == cancel_out.polarization