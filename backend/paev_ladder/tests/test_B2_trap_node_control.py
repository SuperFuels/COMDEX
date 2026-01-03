from ._util import load_result, req_keys

def test_B2_trap_node_control():
    r = load_result("B2_trap_node_control")
    req_keys(r, ["rmse_frac", "dropout_frac"])

    # Pass: position RMSE < 5% travel range; dropout < 10% at moderate speed.
    assert r["rmse_frac"] < 0.05
    assert r["dropout_frac"] < 0.10
