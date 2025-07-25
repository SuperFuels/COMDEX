import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.modules.consciousness.state_manager import STATE

client = TestClient(app)

@pytest.fixture
def mock_container():
    return {
        "id": "test_container",
        "cubes": {
            "0,0,0": {"glyph": "⨀"},
        },
        "metadata": {},
    }

@pytest.fixture(autouse=True)
def setup_state(mock_container):
    STATE.current_container = mock_container

def test_save_snapshot_creates_file(tmp_path):
    os.environ["GLYPHVAULT_STORAGE_DIR"] = str(tmp_path)
    response = client.post("/vault/snapshot/save", json={
        "avatar_state": {"level": 10}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "snapshot_id" in data

def test_list_snapshots_filters(tmp_path):
    os.environ["GLYPHVAULT_STORAGE_DIR"] = str(tmp_path)
    client.post("/vault/snapshot/save", json={"avatar_state": {"level": 10}})
    response = client.get("/vault/snapshot/list")
    assert response.status_code == 200
    assert "snapshots" in response.json()

def test_load_snapshot_success(tmp_path):
    os.environ["GLYPHVAULT_STORAGE_DIR"] = str(tmp_path)
    save_resp = client.post("/vault/snapshot/save", json={"avatar_state": {"level": 10}})
    snapshot_id = save_resp.json()["snapshot_id"]
    response = client.post("/vault/snapshot/load", json={"snapshot_id": snapshot_id, "avatar_state": {"level": 10}})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_load_snapshot_missing_file(tmp_path):
    os.environ["GLYPHVAULT_STORAGE_DIR"] = str(tmp_path)
    response = client.post("/vault/snapshot/load", json={"snapshot_id": "nonexistent", "avatar_state": {"level": 10}})
    assert response.status_code == 404

def test_load_snapshot_bad_data(tmp_path):
    os.environ["GLYPHVAULT_STORAGE_DIR"] = str(tmp_path)
    # manually write bad file
    with open(tmp_path / "badfile.snapshot", "w") as f:
        f.write("not json")
    response = client.post("/vault/snapshot/load", json={"snapshot_id": "badfile", "avatar_state": {"level": 10}})
    assert response.status_code == 500

def test_delete_snapshot_success(tmp_path):
    os.environ["GLYPHVAULT_STORAGE_DIR"] = str(tmp_path)
    save_resp = client.post("/vault/snapshot/save", json={"avatar_state": {"level": 10}})
    snapshot_id = save_resp.json()["snapshot_id"]
    response = client.post("/vault/snapshot/delete", json={"snapshot_id": snapshot_id})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_delete_snapshot_not_found(tmp_path):
    os.environ["GLYPHVAULT_STORAGE_DIR"] = str(tmp_path)
    response = client.post("/vault/snapshot/delete", json={"snapshot_id": "does_not_exist"})
    assert response.status_code == 404