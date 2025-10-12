import math
import pytest

from backend.symatics.signature import Signature
from backend.symatics.normalize import canonical_signature
from backend.symatics.context import Context


def test_identity_passthrough_v01():
    """
    v0.1: canonical_signature() is identity passthrough.
    Amplitude, frequency, phase should be unchanged.
    """
    a = Signature(amplitude=1.2345, frequency=3.333, phase=0.1234, polarization="H")

    res = canonical_signature(a)

    # Fields preserved exactly
    assert math.isclose(res.amplitude, a.amplitude, rel_tol=1e-12)
    assert math.isclose(res.frequency, a.frequency, rel_tol=1e-12)
    assert math.isclose(res.phase, a.phase, rel_tol=1e-12)
    assert res.polarization == a.polarization

    # TODO v0.2+: Snap frequency to nearest lattice point
    # TODO v0.2+: Quantize amplitude to lattice and enforce noise floor
    # TODO v0.2+: Canonicalize phase to [0, 2π)
    # TODO v0.2+: Preserve polarization only if in basis set


def test_context_canonicalizer_hook():
    """
    Context.canonical_signature should delegate to custom canonicalizer.
    """
    def custom_canon(sig: Signature) -> Signature:
        # Defensive: handle case where sig.meta is None
        meta = sig.meta or {}
        return Signature(
            amplitude=42.0,
            frequency=sig.frequency,
            phase=sig.phase,
            polarization=sig.polarization,
            meta={**meta, "custom": True},
        )

    ctx = Context(canonicalizer=custom_canon)
    a = Signature(amplitude=1.0, frequency=2.0, phase=0.5, polarization="H")

    res = ctx.canonical_signature(a)

    # Custom canonicalizer must override amplitude and tag metadata
    assert res.amplitude == 42.0
    assert res.meta.get("custom") is True

    # Ensure canonicalization did not fallback to default
    assert res.meta.get("cnf") is None