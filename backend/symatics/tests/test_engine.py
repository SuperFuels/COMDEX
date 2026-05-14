import math
import pytest
from hypothesis import given, strategies as st

from backend.symatics.signature import Signature
from backend.symatics.operators import OPS, apply_operator
from backend.symatics.engine import eval_expr, parse_expr
from backend.symatics.laws import law_associativity
from backend.symatics.context import Context

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
    assert result.amplitude > 0.0
    assert isinstance(result.frequency, float)
    assert isinstance(result.phase, float)
    assert result.polarization in ("H", "V")
    assert result.meta.get("superposed") is True


def test_measure_superposed_literals():
    """
    Verify that (μ (⊕ 1.0 2.0)) collapses correctly
    into a canonicalized Signature with 'measured' metadata.
    Updated under Tessaris v0.2 - allows inner superposition tagging.
    """
    expr = "(μ (⊕ 1.0 2.0))"
    ast = parse_expr(expr)
    result = eval_expr(ast)

    # Must be a Signature
    assert isinstance(result, Signature)

    # Should preserve amplitude > 0
    assert result.amplitude > 0.0

    # Metadata should show both superposed + measured
    # Legacy: top-level True, v0.2+: inner allowed (None here)
    assert result.meta.get("superposed") in (True, None)
    assert result.meta.get("measured") is True


def test_entanglement_literals():
    """
    Verify that (↔ 1.0 2.0) produces an entangled pair with metadata.
    """
    expr = "(↔ 1.0 2.0)"
    ast = parse_expr(expr)
    result = eval_expr(ast)

    assert isinstance(result, dict)
    assert "left" in result and "right" in result and "meta" in result

    left, right, meta = result["left"], result["right"], result["meta"]

    assert isinstance(left, Signature)
    assert isinstance(right, Signature)
    assert "link_id" in meta
    assert "corr" in meta
    assert isinstance(meta["corr"], dict)


def test_entanglement_symmetry():
    a = sig(amplitude=1.0, frequency=5.0, phase=0.0, polarization="H")
    b = sig(amplitude=2.0, frequency=5.5, phase=0.5, polarization="V")

    ab = OPS["↔"].impl(a, b)
    ba = OPS["↔"].impl(b, a)

    assert isinstance(ab, dict)
    assert isinstance(ba, dict)
    assert isinstance(ab["left"], Signature)
    assert isinstance(ab["right"], Signature)
    assert isinstance(ba["left"], Signature)
    assert isinstance(ba["right"], Signature)

    set_ab = {(ab["left"].frequency, ab["left"].polarization),
              (ab["right"].frequency, ab["right"].polarization)}
    set_ba = {(ba["left"].frequency, ba["left"].polarization),
              (ba["right"].frequency, ba["right"].polarization)}
    assert set_ab == set_ba
    assert "corr" in ab["meta"]
    assert "corr" in ba["meta"]


def test_resonance_near_match_amplifies():
    a = sig(amplitude=1.0, frequency=10.0, phase=0.0, polarization="H")
    b = sig(amplitude=2.0, frequency=10.0 + 1e-7, phase=0.1, polarization="H")
    res = OPS["⟲"].impl(a, b)
    assert res.meta.get("resonant", False) is True
    assert res.amplitude > max(a.amplitude, b.amplitude)


def test_resonance_off_resonance_damps():
    a = sig(amplitude=2.0, frequency=5.0, phase=0.0, polarization="H")
    b = sig(amplitude=1.0, frequency=50.0, phase=1.0, polarization="V")
    res = OPS["⟲"].impl(a, b)
    assert res.meta.get("resonant") is False
    assert res.amplitude < max(a.amplitude, b.amplitude)


def test_projection_retains_if_same_pol():
    a = sig(amplitude=1.0, frequency=5.0, polarization="H")
    res = OPS["π"].impl(a, "H")
    assert res.polarization == "H"
    assert math.isclose(res.amplitude, a.amplitude, rel_tol=1e-6)
    assert res.meta.get("projected") == "H"


def test_projection_attenuates_if_diff_pol():
    a = sig(amplitude=1.0, frequency=5.0, polarization="H")
    res = OPS["π"].impl(a, "V")
    assert res.polarization == "V"
    assert math.isclose(res.amplitude, 0.9, rel_tol=1e-6)
    assert res.meta.get("projected") == "V"


def test_measurement_canonicalizes_and_tags():
    a = sig(amplitude=1.2345, frequency=3.333, phase=0.1234, polarization="H")
    res = OPS["μ"].impl(a)
    assert isinstance(res, Signature)
    assert res.meta.get("measured") is True
    assert isinstance(res.frequency, float)
    assert isinstance(res.phase, float)
    assert res.polarization in ("H", "V")
    assert math.isclose(res.amplitude, a.amplitude, rel_tol=1e-12)

def test_collapse_simple():
    from backend.symatics.operators import OPS
    from backend.symatics.signature import Signature

    # Base state (superposed wave)
    a = Signature(
        amplitude=1.2,
        frequency=5.0,
        phase=0.0,
        polarization="H",
        meta={"superposed": True},
    )

    res = OPS["∇"](a)

    # Must still be a valid Signature
    assert isinstance(res, Signature)

    # Collapse metadata should appear
    assert res.meta.get("collapsed") is True
    assert res.meta.get("measured") is True

    # Should preserve superposition tag
    assert res.meta.get("superposed") is True

    # Amplitude normalized to <= 1.0
    assert 0.0 <= res.amplitude <= 1.0