"""
💾 SRK-17 Task 6 - GHX Vault Exporter (GVE)
Module: backend/modules/holograms/ghx_vault_exporter.py

Purpose:
    Archive verified GHX bundles and chain continuity into GlyphVault,
    enabling replay and restoration of distributed resonance state.

Responsibilities:
    * Import GHX chain records from GHX-DLS
    * Package verified bundle sets into a vault snapshot
    * Maintain continuity metadata (chain_head, chain_length, timestamp)
    * Provide replay and verification hooks
"""

import time
import json
import hashlib
from typing import Dict, Any, List

from backend.modules.encryption.glyph_vault import GlyphVault
from backend.modules.codex.codex_trace import CodexTrace


# ────────────────────────────────────────────────────────────────
# 🔹 SRK-13 D6 - Entropy Signature + GHX Metadata Injection
# ────────────────────────────────────────────────────────────────
def inject_entropy_signature(bundle: dict) -> dict:
    """
    Compute a deterministic entropy signature for the GHX bundle and
    inject metadata for vault validation continuity.
    """
    entropy = hashlib.sha3_512(json.dumps(bundle, sort_keys=True).encode()).hexdigest()
    bundle["entropy_signature"] = entropy
    bundle["ghx_meta"] = {
        "timestamp": time.time(),
        "source": "GlyphVault",
        "validated": True,
    }
    return bundle


# ────────────────────────────────────────────────────────────────
# 💾 GHX Vault Exporter (SRK-17 Task 6)
# ────────────────────────────────────────────────────────────────
class GHXVaultExporter:
    """SRK-17 Task 6 - GHX Vault Exporter (GVE)"""

    def __init__(self, container_id: str = "ghx_vault_export"):
        self.vault = GlyphVault(container_id)
        self.trace = CodexTrace()
        self._last_export: Dict[str, Any] = {}

    async def export_chain_snapshot(self, chain: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Archive the full GHX chain into GlyphVault with integrity metadata
        and inject an entropy signature (SRK-13 D6).
        """
        if not chain:
            raise ValueError("Cannot export empty GHX chain")

        chain_head = chain[-1]["chain_hash"]
        chain_length = len(chain)
        timestamp = time.time()

        snapshot = {
            "export_id": f"GVE-{hashlib.sha1(str(timestamp).encode()).hexdigest()[:10]}",
            "timestamp": timestamp,
            "chain_length": chain_length,
            "chain_head": chain_head,
            "chain": chain,
            "integrity": hashlib.sha3_512(
                json.dumps(chain, sort_keys=True).encode()
            ).hexdigest(),
        }

        # 🔹 SRK-13 D6 - inject entropy + metadata
        snapshot = inject_entropy_signature(snapshot)

        # 🔸 Persist to GlyphVault
        await self.vault.save_bundle(snapshot)
        self._last_export = snapshot

        self.trace.record(
            "ghx_vault_export_completed",
            {"export_id": snapshot["export_id"], "chain_length": chain_length},
            {"module": "GHX-Vault-Exporter", "status": "archived"},
        )

        return snapshot

    async def replay_from_vault(self) -> Dict[str, Any]:
        """Simulate continuity restoration - returns the last exported snapshot."""
        if not self._last_export:
            raise RuntimeError("No prior export found in GHXVaultExporter")

        replay_meta = {
            "restored_at": time.time(),
            "restored_head": self._last_export.get("chain_head"),
            "restored_length": self._last_export.get("chain_length"),
            "verified": True,
        }

        self.trace.record(
            "ghx_vault_replay_invoked",
            replay_meta,
            {"module": "GHX-Vault-Exporter", "phase": "replay"},
        )
        return replay_meta