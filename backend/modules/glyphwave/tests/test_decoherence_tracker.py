import time
import hashlib
import pytest

from backend.modules.glyphwave.decoherence.decoherence_tracker import DecoherenceTracker


@pytest.fixture
def tracker():
    """Create a fresh tracker for each test."""
    return DecoherenceTracker()


def test_fingerprint_stability(tracker):
    wave = {"amplitude": 1.23, "phase": 0.77, "coherence": 0.95, "timestamp": 123456.789}
    fp1 = tracker.fingerprint(wave)
    fp2 = tracker.fingerprint(wave)
    # Same inputs → same fingerprint
    assert fp1 == fp2
    # Verify SHA3-512 length
    assert len(fp1) == 128


def test_track_updates_coherence_and_sqi(tracker):
    eid = "E-TEST"
    tracker.track(eid, 0.9)
    initial = tracker.history[eid]
    assert "ΔC" in initial and "SQI_drift" in initial
    assert round(initial["SQI_drift"], 4) == round((1 - 0.9) ** 2, 4)

    # Update with new coherence → drift should reflect delta
    tracker.track(eid, 0.8)
    updated = tracker.history[eid]
    assert updated["ΔC"] == pytest.approx(-0.1, abs=1e-6)
    assert updated["SQI_drift"] > initial["SQI_drift"]


def test_register_collapse_generates_fingerprint(tracker):
    eid = "E-COLLAPSE"
    tracker.track(eid, 0.7)
    tracker.register_collapse(eid, 0.7)
    assert tracker.last_fingerprint is not None
    assert len(tracker.last_fingerprint) == 128
    assert eid in tracker.history


def test_sequential_tracking_accumulates_history(tracker):
    eid = "E-MULTI"
    coherences = [1.0, 0.95, 0.8, 0.5]
    for c in coherences:
        tracker.track(eid, c)
        time.sleep(0.001)  # Simulate small time gaps

    hist = tracker.history[eid]
    assert "ΔC" in hist
    assert hist["SQI_drift"] >= 0.25  # SQI rises with decoherence
    assert isinstance(hist["timestamp"], float)