import pytest
from photon.executor import execute
from photon.validator import validate_capsule

SAMPLES = [
    ("⊕μ∇", True),
    ("ψ := Wave()", True),
    ("⊕⊕⊕μπ∇", True),
    ("↔↔↔", False),    # no collapse path
    ("∇", False),       # collapse with no state
]

@pytest.mark.parametrize("src,valid", SAMPLES)
def test_language_validity(src, valid):
    try:
        capsule = validate_capsule(src)
        execute(capsule)
        assert valid, f"Expected failure but passed: {src}"
    except Exception:
        assert not valid, f"Expected valid but failed: {src}"