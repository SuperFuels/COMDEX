# backend/modules/glyphnet/glyphnet_utils.py
import time
import logging
from typing import Dict, Any, Optional

from backend.modules.glyphnet.glyphnet_crypto import aes_encrypt_packet
from backend.modules.glyphnet.ephemeral_key_manager import get_ephemeral_key_manager
from backend.modules.glyphnet.qkd_fingerprint import generate_decoherence_fingerprint, collapse_hash

logger = logging.getLogger(__name__)

def create_gip_packet(
    payload: Dict[str, Any],
    sender: str,
    target: Optional[str] = None,
    packet_type: str = "glyph_push",
    encrypt: bool = False,
    public_key_pem: Optional[bytes] = None,
    ephemeral_session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a standardized GlyphNet .gip packet with metadata.
    Supports RSA and ephemeral AES encryption.
    Auto-injects QKD fingerprint + collapse hash if requested.
    """
    packet = {
        "id": f"gip-{int(time.time() * 1000)}",
        "type": packet_type,
        "sender": sender,
        "payload": None,
        "timestamp": time.time(),
        "metadata": metadata.copy() if metadata else {},
    }
    if target:
        packet["target"] = target

    try:
        if encrypt:
            if public_key_pem:
                packet["payload"] = aes_encrypt_packet(payload, public_key_pem)
                packet["type"] = f"{packet_type}_encrypted_rsa"
            elif ephemeral_session_id:
                ephemeral_manager = get_ephemeral_key_manager()
                aes_key = ephemeral_manager.get_key(ephemeral_session_id)
                if aes_key is None:
                    aes_key = ephemeral_manager.generate_key(
                        ephemeral_session_id,
                        trust_level=0.7,
                        emotion_level=0.5,
                        seed_phrase=f"GIP:{sender}->{ephemeral_session_id}",
                    )
                if aes_key:
                    packet["payload"] = aes_encrypt_packet(payload, aes_key)
                    packet["type"] = f"{packet_type}_encrypted_aes_ephemeral"
                    packet["session_id"] = ephemeral_session_id
                else:
                    logger.warning(f"[GlyphNetUtils] No AES key for {ephemeral_session_id}. Sending unencrypted.")
                    packet["payload"] = payload
            else:
                logger.warning("[GlyphNetUtils] Encryption requested but no key provided. Sending unencrypted.")
                packet["payload"] = payload
        else:
            packet["payload"] = payload

        if packet["metadata"].get("qkd_required", False):
            packet["metadata"]["fingerprint"] = generate_decoherence_fingerprint(payload)
            packet["metadata"]["collapse_hash"] = collapse_hash(payload)

    except Exception as e:
        logger.error(f"[GlyphNetUtils] Failed to create packet: {e}")
        raise

    return packet