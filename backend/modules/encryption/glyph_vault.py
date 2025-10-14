"""
🔐 Tessaris GlyphVault — SRK-17 Extension
Back-compat adapter: expose GlyphVault at the expected module path.
Adds async bundle persistence support for GHX Sync Layer.
"""

import asyncio
import json
import time
import hashlib

# Reuse your existing implementation
from .glyphvault_encryptor import GlyphVault as _GlyphVault


# ────────────────────────────────────────────────────────────────
# Extended GlyphVault with SRK-17 GHX bundle persistence
# ────────────────────────────────────────────────────────────────
class GlyphVault(_GlyphVault):
    """Extended GlyphVault providing SRK-17 GHX bundle persistence."""

    async def save_bundle(self, payload: dict):
        """
        🔹 SRK-17: Persist a GHX synchronization bundle.
        Simulates asynchronous persistence into the vault backend.
        """
        bundle_id = payload.get("ghx_id", f"GHX-{int(time.time())}")
        encoded = json.dumps(payload, sort_keys=True).encode()
        checksum = hashlib.sha3_512(encoded).hexdigest()

        # Simulated async I/O to represent persistence latency
        await asyncio.sleep(0.01)

        record = {
            "bundle_id": bundle_id,
            "timestamp": time.time(),
            "checksum": checksum,
            "size": len(encoded),
            "status": "saved",
        }

        # Local record for verification or inspection
        setattr(self, "_last_saved_bundle", record)
        return record


# ────────────────────────────────────────────────────────────────
# Legacy helper functions (preserved)
# ────────────────────────────────────────────────────────────────
def encrypt_to_glyphvault(container_id: str, data: str, context: dict):
    """Legacy helper: encrypt data using GlyphVault."""
    return GlyphVault(container_id).encrypt(data, context)


def decrypt_from_glyphvault(container_id: str, avatar_state: dict):
    """Legacy helper: decrypt data using GlyphVault."""
    return GlyphVault(container_id).decrypt(avatar_state)