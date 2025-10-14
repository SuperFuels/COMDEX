from backend.modules.glyphvault.vault_manager import VaultManager
from backend.modules.glyphwave.qkd.qkd_manager import QKDManager


class GlyphVaultAPI:
    """
    🔹 SRK-13 D7 — GlyphVault API Harmonization Layer
    Integrates VaultManager with QKD metadata synchronization.
    """

    def __init__(self):
        self.vault = VaultManager()
        self.qkd = QKDManager()

    def sync_metadata(self, capsule_id: str) -> dict:
        """
        Inject the active QKD key into the vault capsule metadata and mark it synced.
        """
        entry = self.vault.vault.load(capsule_id)
        entry["meta"]["qkd_key"] = self.qkd.get_active_key()
        entry["meta"]["synced"] = True
        self.vault.vault.save(capsule_id, entry)
        return entry