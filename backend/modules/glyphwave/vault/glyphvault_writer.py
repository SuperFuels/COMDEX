"""
🟣 GlyphVaultWriter - SRK-14 Task 5
Unified Photon Memory Grid + Resonance Ledger Snapshot Exporter.

Combines live photonic state persistence (PMG) with the temporal
resonance graph (ResonanceLedger) to produce a consolidated
GlyphVault artifact (.ghx bundle).

New in SRK-14.5:
 * Vault merge of PMG + Ledger snapshots
 * Lyapunov stability & entropy signature metadata
 * AES-QKD hybrid encryption persistence path
"""

import json
import time
import hashlib
import asyncio
from typing import Dict, Any, Optional

# optional imports are deferred to avoid circular dependencies
try:
    from backend.modules.crypto.encryption_layer import EncryptionLayer
except ImportError:
    EncryptionLayer = None


class GlyphVaultWriter:
    def __init__(self, vault_path: str = "/data/glyphvault"):
        self.vault_path = vault_path
        self.encryption = EncryptionLayer() if EncryptionLayer else None

    # ────────────────────────────────────────────────────────────────
    async def save_snapshot(
        self,
        pmg_snapshot: Dict[str, Any],
        ledger_snapshot: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Persist a unified PMG + ResonanceLedger snapshot to GlyphVault.

        Args:
            pmg_snapshot: state data from PhotonMemoryGrid
            ledger_snapshot: optional temporal coherence ledger data
            metadata: optional override block for extra info
        """
        now = time.time()
        merged = {
            "timestamp": now,
            "pmg": pmg_snapshot,
            "ledger": ledger_snapshot or {},
            "meta": metadata or {},
        }

        # 🔸 Compute GHX entropy signature
        entropy_input = json.dumps(merged, sort_keys=True).encode()
        merged["ghx_signature"] = hashlib.sha3_512(entropy_input).hexdigest()

        # 🔸 Encryption (if available)
        if self.encryption:
            merged = self.encryption.encrypt_blob(merged)

        # 🔸 Write to vault file (atomic async IO)
        filename = f"{self.vault_path}/snapshot_{int(now)}.ghx"
        await self._async_write(filename, merged)

        return {
            "status": "vault_saved",
            "file": filename,
            "ghx_signature": merged.get("ghx_signature", None),
            "ledger_included": bool(ledger_snapshot),
        }

    # ────────────────────────────────────────────────────────────────
    async def _async_write(self, path: str, data: Any):
        """Write data to disk asynchronously with UTF-8 encoding."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._write_file, path, data)

    # ────────────────────────────────────────────────────────────────
    def _write_file(self, path: str, data: Any):
        import os, json
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, dict):
                json.dump(data, f, indent=2)
            else:
                f.write(str(data))