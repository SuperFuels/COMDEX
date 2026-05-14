from backend.modules.glyphwave.vault.vault_restoration import VaultRestoration
from backend.modules.glyphvault.vault_manager import VaultManager

class DummyRuntime:
    def __init__(self):
        self.state = None
    def import_state(self, s): self.state = s

def test_restore_and_rehydrate(tmp_path):
    # Setup
    from backend.modules.glyphvault.key_manager import key_manager
    vm = VaultManager(key_manager.key)
    dummy_state = {"energy": 1.23, "phase": 0.77}
    vm.vault.save("TEST-CAPSULE", {"state": dummy_state})
    restorer = VaultRestoration()
    runtime = DummyRuntime()

    # Exercise
    assert restorer.rehydrate_to_runtime("TEST-CAPSULE", runtime)
    assert runtime.state == dummy_state