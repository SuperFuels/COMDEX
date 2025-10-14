import os
import json
from datetime import datetime
from typing import Optional, List

from backend.modules.glyphvault.container_vault_manager import ContainerVaultManager
from backend.modules.glyphvault.vault_logger import log_event
from backend.modules.glyphvault.vault_audit import VAULT_AUDIT

def get_state():
    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.state_manager_module import StateManager
    return StateManager()  # ✅ instantiate

VAULT_DIR = os.path.join(os.path.dirname(__file__), "../../vault_snapshots")
os.makedirs(VAULT_DIR, exist_ok=True)

class VaultManager:
    def __init__(self, encryption_key: bytes):
        self.encryptor = ContainerVaultManager(encryption_key)

    def _generate_snapshot_filename(self, container_id: str) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        return f"{container_id}_{timestamp}.vault.json"

    def _collapse_if_hoberman(self, container: dict):
        container_type = container.get("container_type", "")
        if container_type in {"hoberman", "symbolic_expansion"}:
            if hasattr(container, "collapse"):
                container.collapse()
            if "cubes" in container:
                del container["cubes"]

    def _inject_ghx_metadata(self, snapshot: dict, container_id: str):
        try:
            from backend.modules.codex.codex_trace import CodexTrace
            from backend.modules.glyphos.glyph_quantum_core import GlyphQuantumCore

            trace = CodexTrace.get_latest_trace(container_id)
            if not trace:
                return

            latest_qglyph = GlyphQuantumCore.get_last_qglyph()
            if not latest_qglyph:
                return

            snapshot["ghx_metadata"] = {
                "ghx_id": trace.get("ghx_id"),
                "qglyph_id": latest_qglyph.get("id"),
                "collapse_trace": trace.get("path"),
                "entropy_signature": latest_qglyph.get("entropy_signature"),
            }
        except Exception as e:
            print(f"[VaultManager] GHX metadata injection skipped: {e}")

    def save_snapshot(self, container_id: str, associated_data: Optional[bytes] = None) -> str:
        container = get_state().current_container
        if not container or container.get("id") != container_id:
            raise ValueError(f"Container {container_id} is not currently active or loaded.")

        self._collapse_if_hoberman(container)
        glyph_data = container.get("cubes", {})

        encrypted_blob = self.encryptor.save_container_glyph_data(glyph_data, associated_data)

        snapshot = {
            "container_id": container_id,
            "saved_on": datetime.utcnow().isoformat(),
            "memory_snapshot": get_state().memory_snapshot,
            "encrypted_glyph_data": encrypted_blob.hex(),
            "runtime_mode": container.get("runtime_mode", "compressed"),
            "container_type": container.get("container_type", "standard")
        }

        self._inject_ghx_metadata(snapshot, container_id)

        filename = self._generate_snapshot_filename(container_id)
        path = os.path.join(VAULT_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

        event_data = {
            "container_id": container_id,
            "filename": filename,
            "timestamp": snapshot["saved_on"]
        }
        log_event("SAVE", event_data)
        VAULT_AUDIT.record_event("SAVE", container_id)

        return filename

    def list_snapshots(self, container_id: Optional[str] = None) -> List[str]:
        files = os.listdir(VAULT_DIR)
        vault_files = [f for f in files if f.endswith(".vault.json")]
        if container_id:
            vault_files = [f for f in vault_files if f.startswith(container_id)]
        return sorted(vault_files, reverse=True)

    def load_snapshot(self, filename: str, associated_data: Optional[bytes] = None, avatar_state: Optional[dict] = None) -> bool:
        path = os.path.join(VAULT_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Snapshot file not found: {filename}")

        with open(path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

        encrypted_hex = snapshot.get("encrypted_glyph_data")
        if not encrypted_hex:
            raise ValueError("Snapshot missing encrypted glyph data.")

        encrypted_blob = bytes.fromhex(encrypted_hex)

        success = self.encryptor.load_container_glyph_data(encrypted_blob, associated_data, avatar_state)

        if success:
            mem_snapshot = snapshot.get("memory_snapshot")
            if mem_snapshot:
                get_state().save_memory_reference(mem_snapshot)

            glyph_map = self.encryptor.get_microgrid().glyph_map
            container = get_state().current_container
            if container is not None:
                cubes = container.setdefault("cubes", {})
                for coord_tuple, meta in glyph_map.items():
                    key = ",".join(map(str, coord_tuple))
                    cubes[key] = meta

                if snapshot.get("container_type") in {"hoberman", "symbolic_expansion"}:
                    if snapshot.get("runtime_mode", "compressed") == "expanded":
                        if hasattr(container, "inflate"):
                            container.inflate()

            log_event("RESTORE", {"filename": filename, "timestamp": datetime.utcnow().isoformat()})
            VAULT_AUDIT.record_event("RESTORE", snapshot.get("container_id", "unknown"))
            return True

        log_event("ACCESS_DENIED", {"filename": filename, "timestamp": datetime.utcnow().isoformat()})
        VAULT_AUDIT.record_event("ACCESS_DENIED", snapshot.get("container_id", "unknown"))
        return False

    def load_container_by_id(self, container_id: str, associated_data: Optional[bytes] = None, avatar_state: Optional[dict] = None) -> bool:
        """
        Loads the most recent snapshot of the given container ID.
        """
        snapshots = self.list_snapshots(container_id)
        if not snapshots:
            raise FileNotFoundError(f"No snapshots found for container: {container_id}")

        latest_snapshot = snapshots[0]
        return self.load_snapshot(latest_snapshot, associated_data, avatar_state)

    def delete_snapshot(self, filename: str) -> bool:
        path = os.path.join(VAULT_DIR, filename)
        if os.path.exists(path):
            os.remove(path)
            log_event("DELETE", {"filename": filename, "timestamp": datetime.utcnow().isoformat()})
            VAULT_AUDIT.record_event("DELETE", "unknown")
            return True
        return False

# 🔐 Vault singleton
from backend.modules.glyphvault.key_manager import key_manager
ENCRYPTION_KEY = key_manager.key
VAULT = VaultManager(ENCRYPTION_KEY)