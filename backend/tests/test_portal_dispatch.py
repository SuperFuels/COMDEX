# backend/tests/test_portal_dispatch.py

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

VALID_TOKEN = "test-token"
VALID_SOURCE = "container-alpha"
VALID_DEST = "container-beta"

@pytest.fixture
def valid_packet():
    return {
        "glyph": "↔",
        "from": VALID_SOURCE,
        "to": VALID_DEST,
        "token": VALID_TOKEN
    }

def test_dispatch_with_invalid_portal():
    """Reject packets with an invalid portal ID or unrecognized route."""
    response = client.post("/api/teleport/invalid_portal_id", json={
        "glyph": "→", "from": VALID_SOURCE, "to": VALID_DEST
    })
    assert response.status_code == 404 or response.status_code == 400
    assert "error" in response.text.lower()

def test_dispatch_with_missing_fields():
    """Reject packets missing required fields like 'glyph', 'from', or 'to'."""
    incomplete_packet = {
        "from": VALID_SOURCE,
        # 'glyph' is missing
        "to": VALID_DEST
    }
    response = client.post("/api/teleport/dispatch", json=incomplete_packet)
    assert response.status_code == 422 or response.status_code == 400
    assert "glyph" in response.text.lower() or "missing" in response.text.lower()

def test_dispatch_from_unregistered_source():
    """Reject teleport packets from unregistered or unknown source containers."""
    unregistered_source = "container-unknown"
    packet = {
        "glyph": "⟲",
        "from": unregistered_source,
        "to": VALID_DEST,
        "token": VALID_TOKEN
    }
    response = client.post("/api/teleport/dispatch", json=packet)
    assert response.status_code in (401, 403, 400)
    assert "unauthorized" in response.text.lower() or "unregistered" in response.text.lower()