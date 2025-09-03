import json
import time
import logging
from typing import Dict, Any

from backend.modules.containers.container_runtime import import_container_state
from backend.modules.encryption.glyph_vault import GlyphVault
from backend.modules.encryption.key_registry import load_public_key
from backend.modules.glyphnet.glyphnet_crypto import decrypt_packet
from backend.modules.glyphnet.glyphnet_logger import log_glyphnet_event
from backend.modules.glyphvault.waveglyph_signer import verify_waveglyph_signature

logger = logging.getLogger(__name__)


def import_encrypted_vault(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decrypts an incoming symbolic container vault using the local private key and imports it into the runtime.
    Verifies the WaveGlyph signature block before importing.
    """
    try:
        encrypted_payload = data.get("payload")
        sender = data.get("sender")
        if not encrypted_payload or not sender:
            return {"status": "error", "error": "Missing payload or sender info"}

        vault = GlyphVault()
        private_key = vault.get_private_key()
        if not private_key:
            return {"status": "error", "error": "No local private key available for decryption"}

        # Decrypt and parse
        decrypted_data = decrypt_packet(encrypted_payload, private_key)
        state = json.loads(decrypted_data)

        # ✅ Signature Block Check
        sig_block = state.get("signature_block")
        signed_by = sig_block.get("signed_by") if sig_block else None
        if not signed_by:
            return {"status": "error", "error": "Missing WaveGlyph signature or signer identity"}

        public_key = load_public_key(signed_by)
        if not public_key:
            return {"status": "error", "error": f"No public key found for signer '{signed_by}'"}

        if not verify_waveglyph_signature(state, public_key):
            return {"status": "error", "error": "WaveGlyph signature verification failed"}

        # Proceed with state import
        container_id = state.get("container_id") or f"imported_{int(time.time())}"
        import_container_state(container_id, state)

        logger.info(f"[VaultImport] Verified + imported container from {sender} as '{container_id}'")
        log_glyphnet_event("vault_import", {"sender": sender, "container_id": container_id, "signed_by": signed_by})

        return {
            "status": "ok",
            "container_id": container_id,
            "timestamp": time.time(),
            "source": sender,
            "signed_by": signed_by
        }

    except Exception as e:
        logger.exception("[VaultImport] Decryption or signature verification failed")
        return {"status": "error", "error": str(e)}