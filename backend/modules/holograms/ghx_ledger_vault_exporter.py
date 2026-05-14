"""
🧩 SRK-18.5 - GHX Ledger Vault Exporter (DLF -> GlyphVault)
Module: backend/modules/holograms/ghx_ledger_vault_exporter.py
Subsystem: Holograms / GHX Continuity Layer

Purpose:
    Provides persistent export and archival of GHX Continuity Ledger snapshots
    into the Tessaris GlyphVault. Enables state restoration, audit recovery,
    and continuity trace replay.

Features:
    * Deterministic SHA3-512 signature for snapshot verification
    * Automatic vault rotation (default max_keep=5)
    * Compatible with GHXContinuityLedger.restore()

Author: Tessaris Core Engineering
Spec Ref: SRK-18 / Phase 18.5
"""

import os
import json
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, Optional
from backend.modules.holograms.ghx_continuity_ledger import GHXContinuityLedger


class GHXVaultExporter:
    """Handles persistent storage and retrieval of GCL snapshots."""

    def __init__(self, vault_root: str = "vault/ledger_snapshots", max_keep: int = 5):
        self.vault_root = vault_root
        self.max_keep = max_keep
        os.makedirs(vault_root, exist_ok=True)

    # ────────────────────────────────────────────────────────────────
    def _compute_snapshot_hash(self, snapshot: Dict[str, Any]) -> str:
        """Compute SHA3-512 digest over canonicalized snapshot."""
        payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha3_512(payload).hexdigest()

    # ────────────────────────────────────────────────────────────────
    def export_snapshot(
        self, ledger: GHXContinuityLedger, container_id: str = "gcl"
    ) -> Dict[str, Any]:
        """Persist a verified snapshot to the GlyphVault."""
        if not ledger.chain:
            raise ValueError("Cannot export empty ledger.")

        snapshot = ledger.snapshot()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        container_dir = os.path.join(self.vault_root, container_id)
        os.makedirs(container_dir, exist_ok=True)

        snap_hash = self._compute_snapshot_hash(snapshot)
        filename = f"{timestamp}_{snap_hash[:12]}.json"
        path = os.path.join(container_dir, filename)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

        # rotate old snapshots
        files = sorted(
            [f for f in os.listdir(container_dir) if f.endswith(".json")],
            reverse=True,
        )
        for old_file in files[self.max_keep:]:
            os.remove(os.path.join(container_dir, old_file))

        return {
            "container": container_id,
            "path": path,
            "hash": snap_hash,
            "timestamp": time.time(),
            "entries": len(snapshot["chain"]),
        }

    # ────────────────────────────────────────────────────────────────
    def load_latest(self, container_id: str = "gcl") -> Optional[GHXContinuityLedger]:
        """Load the most recent snapshot from GlyphVault."""
        container_dir = os.path.join(self.vault_root, container_id)
        if not os.path.exists(container_dir):
            raise FileNotFoundError(f"No vault container found for '{container_id}'.")

        files = sorted(
            [f for f in os.listdir(container_dir) if f.endswith(".json")],
            reverse=True,
        )
        if not files:
            raise FileNotFoundError(f"No snapshots found in container '{container_id}'.")

        latest_path = os.path.join(container_dir, files[0])
        with open(latest_path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

        ledger = GHXContinuityLedger()
        ledger.restore(snapshot)
        return ledger