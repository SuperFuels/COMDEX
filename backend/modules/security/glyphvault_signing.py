# ──────────────────────────────────────────────
#  Tessaris • GlyphVault Signing Module (HQCE Stage 7)
#  Provides signing, verification, and persistence of
#  GHX frames and Morphic Ledger snapshots.
# ──────────────────────────────────────────────

import os
import json
import uuid
import time
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional

from backend.modules.identity.avatar_registry import get_avatar_identity

logger = logging.getLogger(__name__)


class GlyphVaultSigner:
    """
    GlyphVaultSigner handles digital signatures for holographic snapshots,
    GHX overlays, and morphic ledger exports. Uses lightweight HMAC-SHA256
    for deterministic local signing (upgradeable to asymmetric later).
    """

    def __init__(self, vault_path: str = "data/vault"):
        self.vault_path = vault_path
        os.makedirs(self.vault_path, exist_ok=True)
        self.key_store_path = os.path.join(self.vault_path, "glyphvault_keys.json")
        self.keys = self._load_keys()

    # ──────────────────────────────────────────────
    #  Key Handling
    # ──────────────────────────────────────────────
    def _load_keys(self) -> Dict[str, str]:
        if os.path.exists(self.key_store_path):
            try:
                with open(self.key_store_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.warning("[GlyphVaultSigner] Failed to load key store.")
        return {}

    def _save_keys(self):
        try:
            with open(self.key_store_path, "w", encoding="utf-8") as f:
                json.dump(self.keys, f, indent=2)
        except Exception as e:
            logger.error(f"[GlyphVaultSigner] Could not persist key store: {e}")

    def ensure_key(self, avatar_id: str) -> str:
        """Ensure an HMAC key exists for an avatar."""
        if avatar_id not in self.keys:
            self.keys[avatar_id] = uuid.uuid4().hex
            self._save_keys()
            logger.info(f"[GlyphVaultSigner] Generated new vault key for {avatar_id}")
        return self.keys[avatar_id]

    # ──────────────────────────────────────────────
    #  Signing
    # ──────────────────────────────────────────────
    def sign_payload(self, avatar_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Attach signature block to payload."""
        key = self.ensure_key(avatar_id)
        identity = get_avatar_identity(avatar_id)
        payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature = hmac.new(key.encode(), payload_str, hashlib.sha256).hexdigest()

        sig_block = {
            "signature_id": f"sig_{uuid.uuid4().hex[:8]}",
            "avatar_id": avatar_id,
            "signer": identity.get("name", "unknown"),
            "timestamp": time.time(),
            "signature": signature,
            "algorithm": "HMAC-SHA256",
        }

        payload["vault_signature"] = sig_block
        logger.debug(f"[GlyphVaultSigner] Signed payload for {avatar_id} → {sig_block['signature_id']}")
        return payload

    # ──────────────────────────────────────────────
    #  Verification
    # ──────────────────────────────────────────────
    def verify_signature(self, payload: Dict[str, Any]) -> bool:
        """Verify signature integrity of a payload."""
        sig_block = payload.get("vault_signature")
        if not sig_block:
            logger.warning("[GlyphVaultSigner] No signature block found.")
            return False

        avatar_id = sig_block.get("avatar_id")
        key = self.keys.get(avatar_id)
        if not key:
            logger.error(f"[GlyphVaultSigner] Missing key for avatar {avatar_id}")
            return False

        unsigned = {k: v for k, v in payload.items() if k != "vault_signature"}
        payload_str = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected = hmac.new(key.encode(), payload_str, hashlib.sha256).hexdigest()

        if hmac.compare_digest(expected, sig_block.get("signature", "")):
            logger.debug(f"[GlyphVaultSigner] ✅ Verified signature for {avatar_id}")
            return True
        else:
            logger.error(f"[GlyphVaultSigner] ❌ Signature verification failed for {avatar_id}")
            return False

    # ──────────────────────────────────────────────
    #  Persistence Helpers
    # ──────────────────────────────────────────────
    def persist_signed_snapshot(self, payload: Dict[str, Any], label: Optional[str] = None) -> str:
        """Persist signed payload to vault."""
        label = label or f"snapshot_{uuid.uuid4().hex[:8]}"
        out_path = os.path.join(self.vault_path, f"{label}.signed.json")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            logger.info(f"[GlyphVaultSigner] Snapshot saved → {out_path}")
        except Exception as e:
            logger.error(f"[GlyphVaultSigner] Failed to persist snapshot: {e}")
        return out_path


# ──────────────────────────────────────────────
#  Singleton instance
# ──────────────────────────────────────────────
glyphvault_signer = GlyphVaultSigner()