"""
Unit Test - AION Photon Ingest Bridge
────────────────────────────────────────────
Verifies:
    * Correct Φ, R, γ -> ψ, κ, T field mapping
    * Proper invocation of _forward_to_cognitive_fabric()
    * Stable ingestion under partial packets and malformed input
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.AION.photon_bridge.aion_photon_ingest import AIONPhotonIngestor


@pytest.fixture
def ingestor():
    """Initialize a fresh AIONPhotonIngestor with mock forwarding."""
    bridge = AIONPhotonIngestor()
    bridge._forward_to_cognitive_fabric = MagicMock()
    return bridge


def test_full_packet_ingestion(ingestor):
    """Verify correct mapping of all Φ, R, γ -> ψ, κ, T fields."""
    packet = {"Φ": 0.92, "R": 0.81, "γ": 0.75, "S": "stable"}

    ingestor.on_ingest(packet)

    # Check that _forward_to_cognitive_fabric was called
    assert ingestor._forward_to_cognitive_fabric.called, "Fusion forward not invoked."

    payload = ingestor._forward_to_cognitive_fabric.call_args[0][0]

    assert payload["ψ"] == pytest.approx(0.92)
    assert payload["κ"] == pytest.approx(0.81)
    assert payload["T"] == pytest.approx(0.75)
    assert payload["Φ"] == pytest.approx(0.92)
    assert payload["stability"] == "stable"


def test_partial_packet_ingestion(ingestor):
    """Handle missing fields gracefully (partial glyph packets)."""
    packet = {"Φ": 0.99, "R": 1.0}

    ingestor.on_ingest(packet)
    payload = ingestor._forward_to_cognitive_fabric.call_args[0][0]

    # Fields that exist should map correctly
    assert payload["ψ"] == 0.99
    assert payload["κ"] == 1.0
    # Missing γ should yield None
    assert payload["T"] is None


def test_alias_field_names(ingestor):
    """Accept alternate JSON field names (Phi, resonance_index, gain)."""
    packet = {"Phi": 0.88, "resonance_index": 0.95, "gain": 0.72}

    ingestor.on_ingest(packet)
    payload = ingestor._forward_to_cognitive_fabric.call_args[0][0]

    assert payload["ψ"] == pytest.approx(0.88)
    assert payload["κ"] == pytest.approx(0.95)
    assert payload["T"] == pytest.approx(0.72)


def test_invalid_packet_structure(ingestor, caplog):
    """Ensure no crash when non-dict or invalid JSON arrives."""
    bad_inputs = [None, "{}", [], 42]

    for data in bad_inputs:
        with patch.object(ingestor, "log_event") as mock_log:
            try:
                ingestor.on_ingest(data if isinstance(data, dict) else {})
            except Exception as e:
                pytest.fail(f"on_ingest raised unexpectedly: {e}")
            mock_log.assert_called_once()
            mock_log.reset_mock()