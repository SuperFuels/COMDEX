# backend/modules/glyphnet/push_encrypted_packet.py

import logging
from typing import Dict, Optional, Any

from backend.modules.encryption.symbolic_encryption_handler import encrypt_packet_for_identity
from backend.modules.glyphnet.glyphnet_packet import push_symbolic_packet

logger = logging.getLogger(__name__)


def push_encrypted_packet(
    packet: Dict[str, Any],
    target_identity: str,
    sender_identity: Optional[str] = None,
    use_aes_fallback: bool = False
) -> Dict[str, Any]:
    """
    Encrypts a .gip symbolic packet and sends it securely using GlyphPush.

    Args:
        packet: The symbolic .gip packet to send (un-encrypted).
        target_identity: The receiving agent or container identity.
        sender_identity: Optional identity string for sender attribution.
        use_aes_fallback: Whether to allow AES fallback if symbolic encryption fails.

    Returns:
        dict containing status and metadata about the push attempt.
    """
    try:
        # Defensive copy (don't mutate caller's packet dict)
        packet_copy = dict(packet)

        encrypted = encrypt_packet_for_identity(
            packet_copy,
            target_identity,
            use_aes_fallback=use_aes_fallback
        )

        # Attach routing metadata
        encrypted["sender"] = sender_identity or "unknown"
        encrypted["original_type"] = packet_copy.get("type", "symbolic")

        # Push over GlyphNet
        push_symbolic_packet(encrypted)

        logger.info(
            f"[EncryptedPush] Encrypted packet sent "
            f"type={packet_copy.get('type')} -> target={target_identity}"
        )

        return {"status": "ok", "target": target_identity, "method": encrypted.get("method", "unknown")}

    except Exception as e:
        logger.warning(
            f"[EncryptedPush] Failed to send encrypted packet to {target_identity}: {e}",
            exc_info=True
        )
        return {"status": "error", "error": str(e), "target": target_identity}