from backend.modules.glyphvault.vault_manager import VAULT, get_state

# Fake minimal container
test_container = {
    "id": "atom_test_01",
    "runtime_mode": "compressed",
    "container_type": "hoberman",
    "cubes": {
        "0,0,0": {"glyph": "⚛", "label": "origin"}
    }
}

get_state().current_container = test_container
get_state().memory_snapshot = {"note": "fake memory test"}

VAULT.save_snapshot("atom_test_01")
print("✅ Snapshot created for 'atom_test_01'")