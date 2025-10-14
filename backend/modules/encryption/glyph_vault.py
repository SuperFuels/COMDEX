"""
🔐 Tessaris GlyphVault — SRK-17 Extension
Back-compat adapter: exposes GlyphVault at the expected module path.
Adds async GHX bundle persistence support for the GHX Sync Layer.
"""

import os
import json
import time
import asyncio
import hashlib
from cryptography.fernet import Fernet


# ────────────────────────────────────────────────────────────────
# Base GlyphVault — Encrypted local capsule persistence
# ────────────────────────────────────────────────────────────────
class GlyphVault:
    """Encrypted holographic persistence container for photon/symbolic state."""

    def __init__(self, vault_dir="vault/data", key=None):
        os.makedirs(vault_dir, exist_ok=True)
        self.vault_dir = vault_dir
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)

    # ── SRK-13 Core: Encrypted capsule save/load ─────────────────
    def save(self, capsule_id: str, state: dict):
        path = os.path.join(self.vault_dir, f"{capsule_id}.gvx")
        payload = json.dumps(state, indent=2).encode()
        enc = self.cipher.encrypt(payload)
        with open(path, "wb") as f:
            f.write(enc)
        return path

    def load(self, capsule_id: str):
        path = os.path.join(self.vault_dir, f"{capsule_id}.gvx")
        with open(path, "rb") as f:
            enc = f.read()
        return json.loads(self.cipher.decrypt(enc))

    # ── SRK-17 Extension: Async GHX bundle persistence ───────────
    async def save_bundle(self, payload: dict):
        """
        🔹 SRK-17: Persist a GHX synchronization bundle.
        Simulates asynchronous persistence into the vault backend.
        """
        bundle_id = payload.get("ghx_id", f"GHX-{int(time.time())}")
        encoded = json.dumps(payload, sort_keys=True).encode()
        checksum = hashlib.sha3_512(encoded).hexdigest()

        # Simulated async I/O latency
        await asyncio.sleep(0.01)

        record = {
            "bundle_id": bundle_id,
            "timestamp": time.time(),
            "checksum": checksum,
            "size": len(encoded),
            "status": "saved",
        }

        setattr(self, "_last_saved_bundle", record)
        return record


# ────────────────────────────────────────────────────────────────
# Legacy helper functions (SRK-10/11 back-compat)
# ────────────────────────────────────────────────────────────────
def encrypt_to_glyphvault(container_id: str, data: str, context: dict):
    """Encrypt arbitrary data using GlyphVault encryption."""
    gv = GlyphVault(container_id)
    payload = {"data": data, "context": context, "timestamp": time.time()}
    gv.save(container_id, payload)
    return payload


def decrypt_from_glyphvault(container_id: str, avatar_state: dict):
    """Decrypt and recover data using GlyphVault."""
    gv = GlyphVault(container_id)
    return gv.load(container_id)