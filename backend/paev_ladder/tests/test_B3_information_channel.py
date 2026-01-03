from ._util import load_result, req_keys

def test_B3_information_channel():
    r = load_result("B3_information_channel")
    req_keys(r, ["ser_nominal", "snr_db", "ser_curve"])

    # Pass: SER < 5% at nominal SNR with graceful degradation curve.
    assert r["ser_nominal"] < 0.05
    # ser_curve: list of [snr_db, ser]
    curve = r["ser_curve"]
    assert isinstance(curve, list) and len(curve) >= 3
