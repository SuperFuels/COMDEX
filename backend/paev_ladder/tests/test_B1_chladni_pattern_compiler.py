from ._util import load_result, req_keys

def test_B1_chladni_pattern_compiler():
    r = load_result("B1_chladni_pattern_compiler")
    req_keys(r, ["similarities", "robustness_drop"])

    # Pass: similarity ≥ 0.8 on ≥3 distinct target modes
    sims = r["similarities"]  # list[float]
    assert isinstance(sims, list) and len(sims) >= 3
    assert sum(1 for s in sims if s >= 0.8) >= 3

    # robustness drop ≤ 0.1 under small perturbations
    assert r["robustness_drop"] <= 0.1
