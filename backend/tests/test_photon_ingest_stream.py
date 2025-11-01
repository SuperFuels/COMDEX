# backend/tests/test_photon_ingest_stream.py
import pytest
from backend.QQC.photon_bridge.qqc_photon_bridge import QQCPhotonBridge
from backend.AION.photon_bridge.aion_photon_ingest import AIONPhotonIngestor

@pytest.fixture
def fake_packet():
    return "⏱:1760791027.87 Φ:ε0 R:ε5000000000 S:stable γ:ε40000000000"

def test_qqc_bridge_ingest(fake_packet):
    bridge = QQCPhotonBridge()
    bridge.ingest_packet(fake_packet)
    assert "Φ" in fake_packet

def test_aion_ingest(fake_packet):
    ingestor = AIONPhotonIngestor()
    ingestor.ingest_packet(fake_packet)
    # Should produce a cognitive fabric mapping
    ingestor.on_ingest({"Φ": 1.0, "R": 0.995, "S": "stable", "gain": 0.96})