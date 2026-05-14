import json
from pathlib import Path
from backend.AION.telemetry.coherence_tracker import record_coherence, CoherenceTracker, LOG_PATH

def test_coherence_tracker_basic(tmp_path):
    # Redirect log path for isolation
    tracker = CoherenceTracker()
    tracker.records = []  # ensure fresh start

    # simulate a few updates
    summary1 = tracker.update(pass_rate=0.5, tolerance=0.1, status="ok")
    summary2 = tracker.update(pass_rate=0.8, tolerance=0.05, status="ok")

    assert 0 <= summary2["Φ_stability_index"] <= 1
    assert summary2["rolling_avg_pass"] > 0
    assert summary2["window"] == 2

    # check file written
    assert LOG_PATH.exists()
    with open(LOG_PATH, "r") as f:
        lines = [json.loads(l) for l in f.readlines()]
    assert len(lines) >= 2
    assert "Φ_stability_index" in lines[-1]

def test_record_coherence_wrapper(monkeypatch):
    # Patch aion_stream.post_metric to avoid async issues
    monkeypatch.setattr("backend.AION.telemetry.aion_stream.post_metric", lambda n, d: None)
    result = record_coherence(0.9, 0.05, "ok")
    assert "Φ_stability_index" in result
    assert result["rolling_avg_pass"] >= 0