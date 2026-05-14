import pytest

from backend.symatics.primitives import demo_all


@pytest.mark.smoke
def test_demo_all_runs_and_returns_dict():
    """Ensure demo_all executes without errors and returns all expected keys."""
    results = demo_all(print_out=False)

    # It should be a dict with known keys
    expected_keys = {
        "wave1",
        "wave2",
        "superposed",
        "entangled",
        "resonated",
        "collapsed",
        "trigger",
        "tensorized",
        "equivalent",
        "reversible",
        "fused",
        "crystallized",
        "photon_emit",
        "photon_from_wave",
        "collapsed_emit",
    }

    missing = expected_keys - results.keys()
    assert not missing, f"Missing keys in results: {missing}"

    # Quick sanity check on representative values
    assert isinstance(results["wave1"], str)
    assert isinstance(results["entangled"], dict)
    assert "signature" in results["collapsed"]
    assert "photon" in results["collapsed_emit"]