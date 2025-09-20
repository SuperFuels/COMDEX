# File: backend/modules/glyphnet/glyphnet_packet.py

import json
import time
import base64
import logging
from typing import Dict, Any, Optional

# ✅ AES/RSA crypto adapters
from backend.modules.glyphnet.glyphnet_crypto import (
    aes_encrypt_packet,
    aes_decrypt_packet,
    encrypt_packet as crypto_encrypt_packet,
    decrypt_packet as crypto_decrypt_packet,
)

# ✅ Ephemeral session AES manager
from backend.modules.glyphnet.ephemeral_key_manager import get_ephemeral_key_manager

# ✅ Symbolic key derivation
from backend.modules.glyphnet.symbolic_key_derivation import symbolic_key_deriver

# ✅ Abuse protection
from backend.modules.security.rate_limit_manager import rate_limit_manager

# ✅ QKD fingerprint utilities
from backend.modules.glyphnet.qkd_fingerprint import (
    generate_decoherence_fingerprint,
    collapse_hash,
)

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────
# Packet creation + encryption + QKD integrity
# ───────────────────────────────────────────────
from backend.modules.glyphnet.glyphnet_utils import create_gip_packet

# ───────────────────────────────────────────────
# Encode / Decode
# ───────────────────────────────────────────────
def encode_gip_packet(packet: Dict[str, Any]) -> str:
    """Serialize and base64-encode a GlyphNet packet for transmission."""
    try:
        return base64.b64encode(json.dumps(packet).encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"[GlyphNetPacket] Encoding failed: {e}")
        raise


def decode_gip_packet(encoded_packet: str) -> Dict[str, Any]:
    """Decode a base64 GlyphNet packet back into a dict."""
    try:
        return json.loads(base64.b64decode(encoded_packet).decode("utf-8"))
    except Exception as e:
        logger.error(f"[GlyphNetPacket] Decoding failed: {e}")
        raise


# ───────────────────────────────────────────────
# Decryption
# ───────────────────────────────────────────────
def decrypt_gip_packet(encrypted_payload: Any, private_key_pem: bytes) -> Dict[str, Any]:
    """
    Decrypts an encrypted payload into the original dict using RSA or AES.
    Wrapper around glyphnet_crypto.decrypt_packet().
    """
    try:
        return crypto_decrypt_packet(encrypted_payload, rsa_private_key_pem=private_key_pem)
    except Exception as e:
        logger.error(f"[GlyphNetPacket] Decryption failed: {e}")
        raise


# ───────────────────────────────────────────────
# Transmission / Routing
# ───────────────────────────────────────────────
def push_symbolic_packet(
    packet: Dict[str, Any],
    transport: str = "tcp",
    options: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Send the packet into GlyphNet transport system.
    - Enforces rate limiting
    - Routes via glyph_transport_switch (tcp, beacon, radio, light, local, gwave)
    """
    sender_id = packet.get("sender")
    if not rate_limit_manager.allow_request(sender_id):
        logger.warning(f"[AbuseGuard] Rate limit exceeded for sender: {sender_id}. Packet rejected.")
        return False

    try:
        # ✅ Lazy import to avoid circular import
        from backend.modules.glyphnet.glyph_transport_switch import route_gip_packet

        logger.info(
            f"[GlyphNetPacket] 📡 Dispatch {packet.get('id')} from {sender_id} → {packet.get('target', 'broadcast')} "
            f"(type={packet['type']}, transport={transport})"
        )
        return route_gip_packet(packet, transport, options)
    except Exception as e:
        logger.error(f"[GlyphNetPacket] Failed to push packet via {transport}: {e}")
        return False