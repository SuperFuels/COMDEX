import os
import json
import pytest
from backend.modules.glyphvault.vault_manager import VaultManager, VAULT_DIR
from backend.modules.consciousness.state_manager import STATE

TEST_ENCRYPTION_KEY = b"0123456789abcdef0123456789abcdef"

@pytest.fixture(scope="module")
def vault_manager():
    return VaultManager(TEST_ENCRYPTION_KEY)

@pytest.fixture(scope="module")
def test_container():
    container = {
        "id": "vault_test_container",
        "cubes": {
            "0,0,0": {"glyph": "⟦ VaultGlyph ⟧"},
        }
    }
    STATE.current_container = container
    STATE.memory_snapshot = {"vault_test": "✓"}
    yield container
    STATE.current_container = None
    STATE.memory_snapshot = {}

def test_save_and_list_snapshot(vault_manager, test_container):
    filename = vault_manager.save_snapshot(test_container["id"])
    path = os.path.join(VAULT_DIR, filename)
    assert os.path.exists(path)

    files = vault_manager.list_snapshots(test_container["id"])
    assert filename in files

def test_load_snapshot_valid(vault_manager, test_container):
    filename = vault_manager.save_snapshot(test_container["id"])
    STATE.current_container["cubes"] = {}  # simulate change
    avatar_state = {"level": 10}

    result = vault_manager.load_snapshot(filename, avatar_state=avatar_state)
    assert result
    assert "0,0,0" in STATE.current_container["cubes"]
    assert STATE.memory_snapshot.get("vault_test") == "✓"

def test_load_snapshot_invalid_avatar(vault_manager, test_container):
    filename = vault_manager.save_snapshot(test_container["id"])
    STATE.current_container["cubes"] = {}
    avatar_state = {"level": 1}  # Fails Soul Law

    result = vault_manager.load_snapshot(filename, avatar_state=avatar_state)
    assert not result

def test_delete_snapshot(vault_manager, test_container):
    filename = vault_manager.save_snapshot(test_container["id"])
    path = os.path.join(VAULT_DIR, filename)

    assert os.path.exists(path)
    deleted = vault_manager.delete_snapshot(filename)
    assert deleted
    assert not os.path.exists(path)