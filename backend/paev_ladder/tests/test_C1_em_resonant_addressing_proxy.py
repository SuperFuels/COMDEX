from ._util import load_result, req_keys

def test_C1_em_resonant_addressing_proxy():
    r = load_result("C1_em_resonant_addressing_proxy")
    req_keys(r, ["selectivity", "topology_rule_success", "stable_under_detuning"])

    # Pass: selectivity ≥ 5, topology-rule success ≥ 90%, stable under detuning sweep.
    assert r["selectivity"] >= 5.0
    assert r["topology_rule_success"] >= 0.90
    assert r["stable_under_detuning"] is True
