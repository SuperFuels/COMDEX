import os
import pytest
import json
from backend.modules.glyphvault.vault_manager import VaultManager, VAULT_DIR
from backend.modules.consciousness.state_manager import STATE

# Use a valid 32-byte encryption key for tests
TEST_ENCRYPTION_KEY = b"0123456789abcdef0123456789abcdef"

@pytest.fixture(scope="module")
def vault_manager():
    return VaultManager(TEST_ENCRYPTION_KEY)

@pytest.fixture(scope="module")
def test_container():
    # Setup a mock container with cubes and id
    container = {
        "id": "test_container_01",
        "cubes": {
            "0,0,0": {"glyph": "⟦ TestGlyph1 ⟧"},
            "1,1,1": {"glyph": "⟦ TestGlyph2 ⟧"},
        }
    }
    STATE.current_container = container
    # Provide a dummy memory snapshot for restoration validation
    STATE.memory_snapshot = {"memory_key": "memory_value"}
    yield container
    # Cleanup after tests
    STATE.current_container = None
    STATE.memory_snapshot = {}

def test_save_snapshot(vault_manager, test_container):
    filename = vault_manager.save_snapshot(test_container["id"])
    path = os.path.join(VAULT_DIR, filename)
    assert os.path.exists(path), "Snapshot file was not created"

def test_load_snapshot_success(vault_manager, test_container):
    filename = vault_manager.save_snapshot(test_container["id"])
    # Modify current container to simulate change
    STATE.current_container["cubes"] = {}

    # Pass avatar_state with level to pass Soul Law validation
    avatar_state = {"level": 10}

    success = vault_manager.load_snapshot(filename, avatar_state=avatar_state)
    assert success, "Snapshot failed to load"
    # Validate restored cubes
    assert "0,0,0" in STATE.current_container["cubes"], "Cube data not restored"
    # Validate memory snapshot restored
    assert "memory_key" in STATE.memory_snapshot

def test_load_snapshot_missing_file(vault_manager):
    with pytest.raises(FileNotFoundError):
        vault_manager.load_snapshot("non_existent_snapshot.vault.json")

def test_load_snapshot_corrupted_data(vault_manager, test_container):
    filename = vault_manager.save_snapshot(test_container["id"])
    path = os.path.join(VAULT_DIR, filename)
    # Corrupt the snapshot file
    with open(path, "w") as f:
        f.write("INVALID_JSON")
    with pytest.raises(json.JSONDecodeError):
        vault_manager.load_snapshot(filename)

def test_delete_snapshot(vault_manager, test_container):
    filename = vault_manager.save_snapshot(test_container["id"])
    path = os.path.join(VAULT_DIR, filename)
    assert os.path.exists(path)
    success = vault_manager.delete_snapshot(filename)
    assert success, "Snapshot deletion failed"
    assert not os.path.exists(path)