from ._util import load_result, req_keys

def test_C2_two_level_emulator():
    r = load_result("C2_two_level_emulator")
    req_keys(r, ["fidelity", "baseline_fidelity"])

    # Pass: controllable state transitions with fidelity above threshold vs baseline
    assert r["fidelity"] > r["baseline_fidelity"]
    assert r["fidelity"] >= 0.80  # adjust threshold if you want
