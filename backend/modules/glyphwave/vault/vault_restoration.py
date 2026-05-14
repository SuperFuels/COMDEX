"""
🪶 Tessaris SRK-13 D5 - Vault Restoration / Rehydration Protocol
Restores previously saved capsule snapshots from the GlyphVault and
rehydrates them into the active runtime environment.
"""

import time
from typing import Any, Dict
from backend.modules.glyphvault.vault_manager import VaultManager


class VaultRestoration:
    """
    Handles re-loading encrypted capsule snapshots from the GlyphVault and
    re-injecting them into a running Symatic or Photon runtime.

    Typical flow:
        restorer = VaultRestoration()
        state = restorer.restore("CAPSULE-123")
        restorer.rehydrate_to_runtime("CAPSULE-123", runtime)
    """

    def __init__(self):
        self.vm = VaultManager()

    # ───────────────────────────────────────────────
    def restore(self, capsule_id: str) -> Dict[str, Any]:
        """
        Load and decrypt a stored capsule snapshot from the vault.
        Returns the raw state dictionary contained in that capsule.
        """
        data = self.vm.vault.load(capsule_id)
        if "state" not in data:
            raise ValueError(f"[VaultRestoration] Capsule {capsule_id} missing state data.")
        return data["state"]

    # ───────────────────────────────────────────────
    def rehydrate_to_runtime(self, capsule_id: str, runtime: Any) -> bool:
        """
        Load a capsule's state and import it into the active runtime.
        Runtime must implement `import_state(state_dict)`.
        """
        state = self.restore(capsule_id)
        if not hasattr(runtime, "import_state"):
            raise TypeError("[VaultRestoration] Runtime lacks import_state() method.")

        runtime.import_state(state)

        # Optional logging or CodexTrace hook could go here
        print(f"[VaultRestoration] Rehydrated capsule {capsule_id} into runtime at {time.ctime()}")
        return True


# ───────────────────────────────────────────────
# Manual test harness
# ───────────────────────────────────────────────
if __name__ == "__main__":
    class DummyRuntime:
        def import_state(self, state):
            print("Runtime received state:", state)

    # Simulate restoring a capsule
    restorer = VaultRestoration()
    try:
        restorer.rehydrate_to_runtime("TEST-CAPSULE", DummyRuntime())
    except Exception as e:
        print("Test run:", e)