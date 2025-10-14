import os
import pytest
from backend.modules.glyphwave.vault.api_sync import GlyphVaultAPI


class DummyVault:
    """Mock GlyphVault storage."""
    def __init__(self):
        self._store = {}

    def save(self, capsule_id, entry):
        self._store[capsule_id] = entry

    def load(self, capsule_id):
        return self._store[capsule_id]


class DummyVaultManager:
    """Mock VaultManager containing DummyVault."""
    def __init__(self):
        self.vault = DummyVault()


class DummyQKDManager:
    """Mock QKDManager that returns a fake active key."""
    def __init__(self):
        self.calls = 0

    def get_active_key(self):
        self.calls += 1
        return f"QKD-KEY-{self.calls}"


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    """
    Patch VaultManager and QKDManager so the test doesn't touch the real filesystem
    or encryption subsystems.
    """
    monkeypatch.setattr("backend.modules.glyphwave.vault.api_sync.VaultManager", DummyVaultManager)
    monkeypatch.setattr("backend.modules.glyphwave.vault.api_sync.QKDManager", DummyQKDManager)


def test_sync_metadata_injects_qkd_key(tmp_path):
    # Initialize test capsule
    capsule_id = "TEST-CAPSULE"
    api = GlyphVaultAPI()
    api.vault.vault.save(capsule_id, {"meta": {"hash": "abc123"}})

    # Perform metadata sync
    updated = api.sync_metadata(capsule_id)

    # Assertions
    assert "qkd_key" in updated["meta"], "QKD key should be injected into metadata"
    assert updated["meta"]["synced"] is True, "Sync flag should be set"
    assert updated["meta"]["qkd_key"].startswith("QKD-KEY-"), "QKD key format should be valid"
    assert api.vault.vault.load(capsule_id) == updated, "Vault entry should persist updates"