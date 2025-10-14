"""
🔐 Tessaris VaultManager — Unified SRK-13/17 Implementation
Integrates:
 - GlyphVault (Fernet-encrypted capsule persistence)
 - GHX metadata injection (SRK-17)
 - Snapshot save/load/list/delete utilities
 - Vault audit and logging hooks
"""

import os
import json
import time
import hashlib
from datetime import datetime
from typing import Optional, List

from backend.modules.encryption.glyph_vault import GlyphVault
from backend.modules.glyphvault.vault_logger import log_event
from backend.modules.glyphvault.vault_audit import VAULT_AUDIT


# ────────────────────────────────────────────────────────────────
# Runtime state resolver
# ────────────────────────────────────────────────────────────────
def get_state():
    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.state_manager_module import StateManager
    return StateManager()


# ────────────────────────────────────────────────────────────────
# Vault Manager Core
# ────────────────────────────────────────────────────────────────
VAULT_DIR = os.path.join(os.path.dirname(__file__), "../../vault_snapshots")
os.makedirs(VAULT_DIR, exist_ok=True)


class VaultManager:
    """Handles encrypted snapshot persistence and GHX metadata embedding."""

    def __init__(self, key: bytes = None):
        import base64
        key = key or key_manager.key
        safe_key = base64.urlsafe_b64encode(key)
        self.vault = GlyphVault(vault_dir="vault/data", key=safe_key)

    # ───────────────────────────────
    # Utility Helpers
    # ───────────────────────────────
    def _generate_snapshot_filename(self, container_id: str) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        return f"{container_id}_{timestamp}.vault.json"

    def _collapse_if_hoberman(self, container: dict):
        ctype = container.get("container_type", "")
        if ctype in {"hoberman", "symbolic_expansion"}:
            if hasattr(container, "collapse"):
                container.collapse()
            if "cubes" in container:
                del container["cubes"]

    def _inject_ghx_metadata(self, snapshot: dict, container_id: str):
        """SRK-17 — Embed GHX linkage metadata from CodexTrace + QuantumCore."""
        try:
            from backend.modules.codex.codex_trace import CodexTrace
            from backend.modules.glyphos.glyph_quantum_core import GlyphQuantumCore

            trace = CodexTrace.get_latest_trace(container_id)
            qglyph = GlyphQuantumCore.get_last_qglyph()
            if trace and qglyph:
                snapshot["ghx_metadata"] = {
                    "ghx_id": trace.get("ghx_id"),
                    "qglyph_id": qglyph.get("id"),
                    "collapse_trace": trace.get("path"),
                    "entropy_signature": qglyph.get("entropy_signature"),
                }
        except Exception as e:
            print(f"[VaultManager] GHX metadata injection skipped: {e}")

    # ───────────────────────────────
    # Snapshot Lifecycle
    # ───────────────────────────────
    def save_snapshot(self, container_id: str, associated_data: Optional[bytes] = None) -> str:
        state_mgr = get_state()
        container = state_mgr.current_container

        if not container or container.get("id") != container_id:
            raise ValueError(f"Container {container_id} not active or loaded.")

        self._collapse_if_hoberman(container)
        glyph_data = container.get("cubes", {})

        # Compute integrity hash before encryption
        integrity_hash = hashlib.sha3_512(json.dumps(glyph_data, sort_keys=True).encode()).hexdigest()
        encrypted_blob = self.vault.cipher.encrypt(json.dumps(glyph_data).encode())

        snapshot = {
            "container_id": container_id,
            "saved_on": datetime.utcnow().isoformat(),
            "memory_snapshot": state_mgr.memory_snapshot,
            "encrypted_glyph_data": encrypted_blob.hex(),
            "integrity_hash": integrity_hash,
            "runtime_mode": container.get("runtime_mode", "compressed"),
            "container_type": container.get("container_type", "standard"),
        }

        self._inject_ghx_metadata(snapshot, container_id)

        filename = self._generate_snapshot_filename(container_id)
        path = os.path.join(VAULT_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

        log_event("SAVE", {"container_id": container_id, "filename": filename})
        VAULT_AUDIT.record_event("SAVE", container_id)
        return filename

    def list_snapshots(self, container_id: Optional[str] = None) -> List[str]:
        files = [f for f in os.listdir(VAULT_DIR) if f.endswith(".vault.json")]
        if container_id:
            files = [f for f in files if f.startswith(container_id)]
        return sorted(files, reverse=True)

    def load_snapshot(self, filename: str, associated_data: Optional[bytes] = None, avatar_state: Optional[dict] = None) -> bool:
        path = os.path.join(VAULT_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Snapshot not found: {filename}")

        with open(path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

        enc_blob = bytes.fromhex(snapshot["encrypted_glyph_data"])
        glyph_data = json.loads(self.vault.cipher.decrypt(enc_blob).decode())

        # Verify integrity
        integrity_check = hashlib.sha3_512(json.dumps(glyph_data, sort_keys=True).encode()).hexdigest()
        if integrity_check != snapshot["integrity_hash"]:
            raise ValueError("Integrity check failed for snapshot.")

        # Inject recovered data into runtime
        state_mgr = get_state()
        state_mgr.save_memory_reference(snapshot.get("memory_snapshot", {}))
        container = state_mgr.current_container
        if container:
            container.setdefault("cubes", {}).update(glyph_data)

        log_event("RESTORE", {"filename": filename})
        VAULT_AUDIT.record_event("RESTORE", snapshot.get("container_id", "unknown"))
        return True

    def delete_snapshot(self, filename: str) -> bool:
        path = os.path.join(VAULT_DIR, filename)
        if os.path.exists(path):
            os.remove(path)
            log_event("DELETE", {"filename": filename})
            VAULT_AUDIT.record_event("DELETE", "unknown")
            return True
        return False

    # ───────────────────────────────
    # SRK-17 Integration: GHX Bundle
    # ───────────────────────────────
    async def persist_ghx_bundle(self, bundle: dict):
        """SRK-17 async GHX bundle persistence into GlyphVault."""
        return await self.vault.save_bundle(bundle)


# ────────────────────────────────────────────────────────────────
# Singleton Instance
# ────────────────────────────────────────────────────────────────
from backend.modules.glyphvault.key_manager import key_manager
ENCRYPTION_KEY = key_manager.key
VAULT = VaultManager(ENCRYPTION_KEY)