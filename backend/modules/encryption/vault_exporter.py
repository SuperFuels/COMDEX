import json
import time
import logging
from typing import Dict, Any, Optional

from backend.modules.containers.container_runtime import get_container_by_id
from backend.modules.encryption.glyph_vault import GlyphVault
from backend.modules.glyphnet.glyphnet_crypto import encrypt_packet
from backend.modules.glyphnet.glyphnet_packet import push_symbolic_packet
from backend.modules.glyphnet.glyphnet_logger import log_glyphnet_event

logger = logging.getLogger(__name__)


def export_container_vault(container_id: str, target_id: Optional[str] = None, push: bool = False) -> Dict[str, Any]:
    """
    Retrieves symbolic state from a container and encrypts it using the target's public key.
    Optionally pushes to GlyphNet. Returns encrypted payload or plaintext snapshot.
    """
    try:
        container = get_container_by_id(container_id)
        if not container:
            return {"status": "error", "error": f"Container '{container_id}' not found"}

        state = container.export_state()
        vault = GlyphVault(container_id)
        snapshot = vault.create_snapshot(state)
        timestamp = time.time()

        if target_id:
            public_key = vault.get_public_key(target_id)
            if public_key:
                encrypted_payload = encrypt_packet(snapshot, public_key)

                if push:
                    packet = {
                        "type": "vault_export_encrypted",
                        "sender": "vault_exporter",
                        "target": target_id,
                        "payload": encrypted_payload,
                        "timestamp": timestamp,
                    }
                    push_symbolic_packet(packet)
                    log_glyphnet_event("vault_export_encrypted", {"target": target_id})

                return {
                    "status": "ok",
                    "container": container_id,
                    "encrypted": True,
                    "target": target_id,
                    "timestamp": timestamp,
                    "payload": encrypted_payload
                }

            logger.warning(f"[VaultExport] No public key found for {target_id}")
            return {
                "status": "error",
                "error": f"No public key for target '{target_id}'"
            }

        # Unencrypted path
        if push:
            packet = {
                "type": "vault_export",
                "sender": "vault_exporter",
                "payload": snapshot,
                "timestamp": timestamp,
            }
            push_symbolic_packet(packet)
            log_glyphnet_event("vault_export", {"container": container_id})

        return {
            "status": "ok",
            "container": container_id,
            "encrypted": False,
            "payload": snapshot,
            "timestamp": timestamp
        }

    except Exception as e:
        logger.exception(f"[VaultExport] Failed to export container '{container_id}'")
        return {"status": "error", "error": str(e)}