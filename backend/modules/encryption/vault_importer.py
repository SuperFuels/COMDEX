import json
import time
import logging
from typing import Dict, Any

from backend.modules.containers.container_runtime import import_container_state
from backend.modules.encryption.glyph_vault import GlyphVault
from backend.modules.glyphnet.glyphnet_crypto import decrypt_packet
from backend.modules.glyphnet.glyphnet_logger import log_glyphnet_event

logger = logging.getLogger(__name__)


def import_encrypted_vault(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decrypts an incoming symbolic container vault using the local private key and imports it into the runtime.
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

        container_id = state.get("container_id") or f"imported_{int(time.time())}"
        import_container_state(container_id, state)

        logger.info(f"[VaultImport] Imported container from {sender} as '{container_id}'")
        log_glyphnet_event("vault_import", {"sender": sender, "container_id": container_id})

        return {
            "status": "ok",
            "container_id": container_id,
            "timestamp": time.time(),
            "source": sender
        }

    except Exception as e:
        logger.exception("[VaultImport] Decryption or import failed")
        return {"status": "error", "error": str(e)}