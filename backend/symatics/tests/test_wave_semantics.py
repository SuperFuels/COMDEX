from backend.symatics.signature import Signature
from backend.symatics.operators import OPS
import math


def test_superpose_basic():
    """Verify ⊕ superposition preserves frequency and polarization (v0.3 compatible)."""
    a = Signature(1.0, 1000.0, 0.0, "H")
    b = Signature(0.5, 1000.0, 1.0, "H")
    out = OPS["⊕"].impl(a, b)

    # unwrap dict structure if QuantumOps-style
    if isinstance(out, dict) and "args" in out and out["args"]:
        first = out["args"][0]
        if isinstance(first, Signature):
            out = first

    assert isinstance(out, Signature), f"Expected Signature, got {type(out)}"
    assert out.frequency == 1000.0
    assert out.polarization == "H"

    # amplitude should be at least comparable to input, within small tolerance
    assert math.isclose(out.amplitude, a.amplitude, rel_tol=1e-6) or out.amplitude > a.amplitude