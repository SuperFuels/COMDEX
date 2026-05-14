from ._util import load_result, req_keys

def test_C4_multinode_structural_hold():
    r = load_result("C4_multinode_structural_hold")
    req_keys(r, ["hold_seconds", "shape_error_bound", "recovery_rate", "beats_independent_traps"])

    # Pass: stable hold for T seconds with bounded shape error
    assert r["hold_seconds"] > 0
    assert r["shape_error_bound"] is True

    # recovery after perturbation in ≥80% trials
    assert r["recovery_rate"] >= 0.80

    # beats “5 independent traps” baseline
    assert r["beats_independent_traps"] is True
