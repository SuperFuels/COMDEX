import math
import pytest
from hypothesis import given, strategies as st

from backend.symatics.signature import Signature
from backend.symatics.operators import OPS, apply_operator
from backend.symatics.engine import eval_expr, parse_expr
from backend.symatics.laws import law_associativity
from backend.symatics.context import Context
import pytest

pytestmark = pytest.mark.legacy  # mark all old tests
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sig(amplitude=1.0, frequency=1.0, phase=0.0, polarization="H"):
    return Signature(amplitude=amplitude, frequency=frequency, phase=phase, polarization=polarization)


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

def test_superpose_simple():
    expr = "(⊕ 1.0 2.0)"
    ast = parse_expr(expr)
    result = eval_expr(ast)
    assert isinstance(result, Signature)
    assert math.isclose(result.amplitude, 3.0, rel_tol=1e-6)


def test_resonance_amplify():
    a = sig(amplitude=1.0, frequency=5.0, phase=0.0)
    b = sig(amplitude=2.0, frequency=5.0, phase=0.1)
    res = OPS["⟲"].impl(a, b)
    assert res.meta.get("resonant", False) is True
    assert res.amplitude > max(a.amplitude, b.amplitude)


def test_measure_snap():
    a = sig(amplitude=1.2345, frequency=3.333, phase=0.1234)
    res = OPS["μ"].impl(a)
    assert res.meta.get("measured") is True
    assert isinstance(res, Signature)


def test_projection():
    a = sig(amplitude=1.0, frequency=5.0, polarization="H")
    res = OPS["π"].impl(a, "V")
    assert res.polarization == "V"
    assert math.isclose(res.amplitude, 0.9, rel_tol=1e-6)


# ---------------------------------------------------------------------------
# Law Tests
# ---------------------------------------------------------------------------

def test_associativity_superposition():
    assert law_associativity(trials=20) is True


# ---------------------------------------------------------------------------
# Property-Based Tests
# ---------------------------------------------------------------------------

@given(
    amp1=st.floats(min_value=0.1, max_value=10),
    amp2=st.floats(min_value=0.1, max_value=10),
    freq=st.floats(min_value=1.0, max_value=100),
    phase=st.floats(min_value=0, max_value=2*math.pi),
)
def test_superpose_commutative_when_equal_freq_pol(amp1, amp2, freq, phase):
    a = sig(amplitude=amp1, frequency=freq, phase=phase, polarization="H")
    b = sig(amplitude=amp2, frequency=freq, phase=phase, polarization="H")

    left = OPS["⊕"].impl(a, b)
    right = OPS["⊕"].impl(b, a)

    assert math.isclose(left.amplitude, right.amplitude, rel_tol=1e-6)
    assert math.isclose(left.phase, right.phase, rel_tol=1e-6)
    assert left.polarization == right.polarization

def test_superpose_literals_ctx():
    """
    Verify that (⊕ 1.0 2.0) parses correctly into Signatures
    and evaluates to a valid canonicalized Signature.
    """
    expr = "(⊕ 1.0 2.0)"
    ast = parse_expr(expr)
    result = eval_expr(ast)

    # Must be a Signature, not None/dict
    assert isinstance(result, Signature)

    # Amplitude should be the sum in phasor-space (> 0)
    assert result.amplitude > 0.0

    # Frequency/phase/polarization should not be missing
    assert isinstance(result.frequency, float)
    assert isinstance(result.phase, float)
    assert result.polarization in ("H", "V")

    # Metadata should include 'superposed'
    assert result.meta.get("superposed") is True

    # TODO v0.2+: Add phasor-based check where interference (phase difference)
    #             can reduce amplitude (destructive interference), not always sum.
    # TODO v0.2+: Enforce associativity within tolerance bands when destructive
    #             interference is modeled (not exact equality)

def test_measure_superposed_literals():
    """
    Verify that (μ (⊕ 1.0 2.0)) collapses correctly
    into a canonicalized Signature with 'measured' metadata.
    """
    expr = "(μ (⊕ 1.0 2.0))"
    ast = parse_expr(expr)
    result = eval_expr(ast)

    # Must be a Signature
    assert isinstance(result, Signature)

    # Should preserve amplitude > 0
    assert result.amplitude > 0.0

    # Metadata should show both superposed + measured
    assert result.meta.get("superposed") is True
    assert result.meta.get("measured") is True

def test_entanglement_literals():
    """
    Verify that (↔ 1.0 2.0) produces an entangled pair with metadata.
    """
    expr = "(↔ 1.0 2.0)"
    ast = parse_expr(expr)
    result = eval_expr(ast)

    # Entanglement returns a dict with 'left', 'right', and 'meta'
    assert isinstance(result, dict)
    assert "left" in result and "right" in result and "meta" in result

    left, right, meta = result["left"], result["right"], result["meta"]

    # Left and right must be Signatures
    assert isinstance(left, Signature)
    assert isinstance(right, Signature)

    # Meta should contain a stable link_id and correlation fingerprint
    assert "link_id" in meta
    assert "corr" in meta
    assert isinstance(meta["corr"], dict)

    # TODO v0.2+: Add nonlocal correlation check across contexts,
    #             verifying that changes to left propagate to right

def test_entanglement_symmetry():
    """
    Verify that ↔ is symmetric:
    ↔(a, b) and ↔(b, a) should yield entangled pairs
    with equivalent left/right Signatures (ignoring link_id hash order).
    """
    a = sig(amplitude=1.0, frequency=5.0, phase=0.0, polarization="H")
    b = sig(amplitude=2.0, frequency=5.5, phase=0.5, polarization="V")

    ab = OPS["↔"].impl(a, b)
    ba = OPS["↔"].impl(b, a)

    # Both must be dict entanglements
    assert isinstance(ab, dict)
    assert isinstance(ba, dict)

    # Check that the left/right values are Signatures
    assert isinstance(ab["left"], Signature)
    assert isinstance(ab["right"], Signature)
    assert isinstance(ba["left"], Signature)
    assert isinstance(ba["right"], Signature)

    # Symmetry check: sets of (freq, pol) must match regardless of order
    set_ab = {(ab["left"].frequency, ab["left"].polarization),
              (ab["right"].frequency, ab["right"].polarization)}
    set_ba = {(ba["left"].frequency, ba["left"].polarization),
              (ba["right"].frequency, ba["right"].polarization)}

    assert set_ab == set_ba

    # Meta correlation fingerprints must exist
    assert "corr" in ab["meta"]
    assert "corr" in ba["meta"]

def test_resonance_near_match_amplifies():
    """
    ⟲ should amplify when frequencies are nearly equal.
    """
    a = sig(amplitude=1.0, frequency=10.0, phase=0.0, polarization="H")
    b = sig(amplitude=2.0, frequency=10.0 + 1e-7, phase=0.1, polarization="H")

    res = OPS["⟲"].impl(a, b)

    # Must be marked resonant
    assert res.meta.get("resonant", False) is True
    # Amplitude should exceed the max input amplitude
    assert res.amplitude > max(a.amplitude, b.amplitude)

    # TODO v0.2+: Include Q-factor models and decay times;
    #             verify amplitude growth follows resonance envelope physics


def test_resonance_off_resonance_damps():
    """
    ⟲ should softly select one signature and damp when far from resonance.
    """
    a = sig(amplitude=2.0, frequency=5.0, phase=0.0, polarization="H")
    b = sig(amplitude=1.0, frequency=50.0, phase=1.0, polarization="V")

    res = OPS["⟲"].impl(a, b)

    # Should not be resonant
    assert res.meta.get("resonant") is False
    # Amplitude should be slightly reduced (damped)
    assert res.amplitude < max(a.amplitude, b.amplitude)

def test_projection_retains_if_same_pol():
    """
    π should preserve amplitude if projecting into the same polarization.
    """
    a = sig(amplitude=1.0, frequency=5.0, polarization="H")
    res = OPS["π"].impl(a, "H")

    # Polarization should remain unchanged
    assert res.polarization == "H"
    # Amplitude should be preserved
    assert math.isclose(res.amplitude, a.amplitude, rel_tol=1e-6)
    # Metadata should record projection
    assert res.meta.get("projected") == "H"


def test_projection_attenuates_if_diff_pol():
    """
    π should attenuate amplitude when projecting into a different polarization.
    """
    a = sig(amplitude=1.0, frequency=5.0, polarization="H")
    res = OPS["π"].impl(a, "V")

    # Polarization should change
    assert res.polarization == "V"
    # Amplitude should be reduced (×0.9)
    assert math.isclose(res.amplitude, 0.9, rel_tol=1e-6)
    # Metadata should record projection
    assert res.meta.get("projected") == "V"

    # TODO v0.2+: Extend polarization projection with Jones calculus
    #             and full complex vector rotation, not just ×0.9 attenuation

def test_measurement_canonicalizes_and_tags():
    """
    μ should collapse a Signature into canonical form
    and add a 'measured' metadata tag.
    """
    a = sig(amplitude=1.2345, frequency=3.333, phase=0.1234, polarization="H")
    res = OPS["μ"].impl(a)

    # Result must still be a Signature
    assert isinstance(res, Signature)

    # Metadata should include 'measured'
    assert res.meta.get("measured") is True

    # Canonicalization should not lose fields
    assert isinstance(res.frequency, float)
    assert isinstance(res.phase, float)
    assert res.polarization in ("H", "V")

    # v0.1: canonical_signature() is identity passthrough → amplitudes equal
    assert math.isclose(res.amplitude, a.amplitude, rel_tol=1e-12)

    # TODO v0.2+: Verify quantization of amplitude/frequency to lattice
    #             instead of passthrough identity
    # TODO v0.2+: When canonical_signature() introduces quantization lattices,
    #             assert amplitude != original amplitude

    # TODO v0.2+: when canonical_signature() introduces quantization lattices,
    # this check should flip to assert that amplitude != a.amplitude