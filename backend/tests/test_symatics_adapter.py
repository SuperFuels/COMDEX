from backend.symatics.aion_symatics_state_adapter import AionSymaticsStateAdapter


def test_symatics_adapter_normalizes_packet():
    pkt = AionSymaticsStateAdapter.adapt({
        "S1": 0.8,
        "S2": 0.7,
        "S4": 0.3,
        "E": 0.6,
        "H": 0.4,
        "resonance": 0.75,
        "coherence": 0.65,
        "delta_phi": 0.12,
    })

    assert 0.0 <= pkt["coherence"] <= 1.0
    assert 0.0 <= pkt["delta_phi"] <= 1.0
    assert 0.0 <= pkt["entropy"] <= 1.0
    assert 0.0 <= pkt["self_awareness"] <= 1.0
    assert 0.0 <= pkt["global_coherence"] <= 1.0
    assert "symatics" in pkt
    assert pkt["symatics"]["S1"] == 0.8
    assert pkt["symatics"]["S2"] == 0.7