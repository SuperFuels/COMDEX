from symatics.signature import Signature
from symatics.operators import OPS

def test_superpose_basic():
    a = Signature(1.0, 1000.0, 0.0, "H")
    b = Signature(0.5, 1000.0, 1.0, "H")
    out = OPS["⊕"].impl(a,b)
    assert out.frequency == 1000.0
    assert out.polarization == "H"
    assert out.amplitude > a.amplitude