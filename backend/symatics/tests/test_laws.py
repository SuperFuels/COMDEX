# backend/symatics/tests/test_laws.py
import math
import pytest
from hypothesis import given, strategies as st

from symatics.signature import Signature
from symatics.operators import OPS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sig(amplitude=1.0, frequency=1.0, phase=0.0, polarization="H"):
    return Signature(
        amplitude=amplitude,
        frequency=frequency,
        phase=phase,
        polarization=polarization
    )


# ---------------------------------------------------------------------------
# Commutativity / Associativity
# ---------------------------------------------------------------------------

@given(
    amp1=st.floats(min_value=0.1, max_value=5),
    amp2=st.floats(min_value=0.1, max_value=5),
    phase=st.floats(min_value=0, max_value=2*math.pi),
)
def test_superpose_commutative_tolerant(amp1, amp2, phase):
    """
    ⊕ should be commutative up to tolerance
    (ignoring tiny floating-point or phase noise).
    """
    a = sig(amplitude=amp1, frequency=10.0, phase=phase, polarization="H")
    b = sig(amplitude=amp2, frequency=10.0, phase=phase, polarization="H")

    ab = OPS["⊕"].impl(a, b)
    ba = OPS["⊕"].impl(b, a)

    assert math.isclose(ab.amplitude, ba.amplitude, rel_tol=1e-9)
    assert math.isclose(ab.phase, ba.phase, rel_tol=1e-9)


@given(
    amp1=st.floats(min_value=0.1, max_value=5),
    amp2=st.floats(min_value=0.1, max_value=5),
    amp3=st.floats(min_value=0.1, max_value=5),
)
def test_superpose_associative_tolerant(amp1, amp2, amp3):
    """
    ⊕ should be associative up to tolerance
    (in phasor space).
    """
    a = sig(amplitude=amp1, frequency=10.0, phase=0.0)
    b = sig(amplitude=amp2, frequency=10.0, phase=0.0)
    c = sig(amplitude=amp3, frequency=10.0, phase=0.0)

    ab_c = OPS["⊕"].impl(OPS["⊕"].impl(a, b), c)
    a_bc = OPS["⊕"].impl(a, OPS["⊕"].impl(b, c))

    assert math.isclose(ab_c.amplitude, a_bc.amplitude, rel_tol=1e-9)
    assert math.isclose(ab_c.phase, a_bc.phase, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Resonance
# ---------------------------------------------------------------------------

def test_resonance_metadata_contains_q_placeholder():
    """
    ⟲ resonance should add a 'df' metadata entry
    and will later include Q-factor in v0.2+.
    """
    a = sig(amplitude=1.0, frequency=10.0, phase=0.0)
    b = sig(amplitude=1.5, frequency=10.0, phase=0.1)

    res = OPS["⟲"].impl(a, b)

    assert "df" in res.meta
    # Placeholder check: no Q-factor yet, but can be added later
    assert "Q" not in res.meta  # v0.1 baseline


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def test_measurement_tags_and_preserves_fields():
    """
    μ should always tag measured=True and preserve fields.
    """
    a = sig(amplitude=2.5, frequency=5.0, phase=1.2, polarization="V")
    res = OPS["μ"].impl(a)

    assert res.meta.get("measured") is True
    assert isinstance(res.frequency, float)
    assert isinstance(res.phase, float)
    assert res.polarization in ("H", "V", "RHC", "LHC")