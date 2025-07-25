import logging
from typing import Dict, Optional

from backend.modules.encryption.symbolic_encryption_handler import encrypt_packet_for_identity
from backend.modules.glyphnet.glyphnet_packet import push_symbolic_packet

logger = logging.getLogger(__name__)


def push_encrypted_packet(packet: Dict, target_identity: str, sender_identity: Optional[str] = None, use_aes_fallback: bool = False):
    """
    Encrypts a .gip symbolic packet and sends it securely using GlyphPush.
    """
    try:
        encrypted = encrypt_packet_for_identity(packet, target_identity, use_aes_fallback=use_aes_fallback)

        encrypted["sender"] = sender_identity or "unknown"
        encrypted["original_type"] = packet.get("type", "symbolic")

        push_symbolic_packet(encrypted)
        logger.info(f"[EncryptedPush] Encrypted packet sent to {target_identity}")

    except Exception as e:
        logger.warning(f"[EncryptedPush] Failed to send encrypted packet: {e}")