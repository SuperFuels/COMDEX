import time
from backend.AION.fabric import aion_fabric_resonance as fabric

def test_resonance_ingest_and_retrieve():
    fabric.clear_fusion_buffer()
    pkt = {"ψ": 1.0, "κ": 0.9, "T": 0.8, "Φ": 1.0, "stability": "ok"}

    result = fabric.resonance_ingest(pkt)
    assert result is True

    buf = fabric.get_fusion_buffer()
    assert len(buf) == 1
    assert "timestamp" in buf[0]
    assert buf[0]["ψ"] == 1.0

def test_invalid_packet_rejected():
    fabric.clear_fusion_buffer()
    assert fabric.resonance_ingest("bad") is False
    assert len(fabric.get_fusion_buffer()) == 0

def test_fuse_resonance_window_basic():
    from backend.AION.fabric import aion_fabric_resonance as fabric

    fabric.clear_fusion_buffer()
    for i in range(5):
        fabric.resonance_ingest({"ψ": 1.0 - i*0.1, "κ": 0.9, "T": 0.8, "Φ": 1.0, "stability": "ok"})
    fused = fabric.fuse_resonance_window(window_size=5)
    assert fused is not None
    assert 0.0 <= fused["σ"] <= 1.0
    assert abs(fused["ψ̄"] - 0.8) < 0.05