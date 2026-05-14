# ============================================================
# ✅ Test: Photon Replay API Integration
# ============================================================

import os
import json
import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app and route
from fastapi import FastAPI
from backend.api.photon_replay_api import router as photon_replay_router

# Create a mock app to isolate this API
app = FastAPI()
app.include_router(photon_replay_router)

client = TestClient(app)

# Directory where telemetry is stored
TELEMETRY_DIR = "artifacts/telemetry"
os.makedirs(TELEMETRY_DIR, exist_ok=True)


@pytest.fixture(scope="module", autouse=True)
def setup_mock_telemetry():
    """Create a mock .ptn telemetry file for testing."""
    sample_path = os.path.join(TELEMETRY_DIR, "test_photon_snapshot.ptn")
    sample_data = {
        "timestamp": "2025-10-29T12:00:00Z",
        "container_id": "test_container",
        "state": {
            "resonance": {"seq": "⊕↔μ⟲", "intensity": 0.9},
        },
        "sqi_feedback": {"sqi_score": 1.0, "entropy": 0.0, "coherence": 1.0},
        "qqc_feedback": {"qqc_energy": 1.0, "qqc_harmonics": []},
    }
    with open(sample_path, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, indent=2)
    yield
    # Cleanup
    if os.path.exists(sample_path):
        os.remove(sample_path)


def test_available_snapshots():
    """Ensure available snapshots are listed properly."""
    res = client.get("/api/photon/available_snapshots")
    assert res.status_code == 200
    data = res.json()
    assert "snapshots" in data
    assert any("test_photon_snapshot.ptn" in s for s in data["snapshots"])
    print("✅ Snapshot listing OK.")


def test_replay_timeline(monkeypatch):
    """Test replay route with reinjection enabled."""

    async def mock_replay_timeline(limit, broadcast, delay, reinject, container_id):
        # Simulate a short replay
        return [
            {
                "timestamp": "2025-10-29T12:00:01Z",
                "seq": "⊕↔μ⟲",
                "intensity": 0.9,
                "sqi_feedback": {"sqi_score": 1.0},
                "qqc_feedback": {"qqc_energy": 1.0},
            }
        ]

    # Patch replay_timeline to bypass actual async behavior
    import backend.modules.photonlang.integrations.photon_timeline_replay as replay_module
    monkeypatch.setattr(replay_module, "replay_timeline", mock_replay_timeline)

    res = client.get("/api/photon/replay_timeline?reinjection=true&limit=1")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert isinstance(data["frames"], list)
    print("✅ Replay timeline route OK (reinjection stubbed).")