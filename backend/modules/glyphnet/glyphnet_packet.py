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

# ✅ Transport switch integration
from backend.modules.glyphnet.glyph_transport_switch import route_gip_packet

# ✅ QKD fingerprint utilities
from backend.modules.glyphnet.qkd_fingerprint import (
    generate_decoherence_fingerprint,
    collapse_hash,
)

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────
# Packet creation + encryption + QKD integrity
# ───────────────────────────────────────────────
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
        # ── Encryption Path ──
        if encrypt:
            if public_key_pem:
                # 🔒 RSA encrypt
                encrypted_payload = aes_encrypt_packet(payload, public_key_pem)
                packet["payload"] = encrypted_payload
                packet["type"] = f"{packet_type}_encrypted_rsa"

            elif ephemeral_session_id:
                # 🔑 AES ephemeral key path
                ephemeral_manager = get_ephemeral_key_manager()
                symbolic_trust = 0.7
                symbolic_emotion = 0.5
                seed_phrase = f"GIP:{sender}->{ephemeral_session_id}"

                aes_key = ephemeral_manager.get_key(ephemeral_session_id)
                if aes_key is None:
                    aes_key = ephemeral_manager.generate_key(
                        ephemeral_session_id,
                        trust_level=symbolic_trust,
                        emotion_level=symbolic_emotion,
                        seed_phrase=seed_phrase,
                    )

                if aes_key:
                    encrypted_payload = aes_encrypt_packet(payload, aes_key)
                    packet["payload"] = encrypted_payload
                    packet["type"] = f"{packet_type}_encrypted_aes_ephemeral"
                    packet["session_id"] = ephemeral_session_id
                else:
                    logger.warning(
                        f"[GlyphNetPacket] No ephemeral AES key for {ephemeral_session_id}. Sending unencrypted."
                    )
                    packet["payload"] = payload
            else:
                logger.warning("[GlyphNetPacket] Encryption requested but no key provided. Sending unencrypted.")
                packet["payload"] = payload
        else:
            packet["payload"] = payload

        # ── QKD Integrity Injection ──
        if packet["metadata"].get("qkd_required", False):
            try:
                fingerprint = generate_decoherence_fingerprint(payload)
                c_hash = collapse_hash(payload)
                packet["metadata"]["fingerprint"] = fingerprint
                packet["metadata"]["collapse_hash"] = c_hash
                logger.debug(
                    f"[GlyphNetPacket] QKD integrity fields attached (fp+hash) for packet {packet['id']}"
                )
            except Exception as e:
                logger.error(
                    f"[GlyphNetPacket] Failed to generate QKD metadata for packet {packet['id']}: {e}"
                )

    except Exception as e:
        logger.error(f"[GlyphNetPacket] Payload encryption/QKD injection failed: {e}")
        raise

    return packet


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
        logger.info(
            f"[GlyphNetPacket] 📡 Dispatch {packet.get('id')} from {sender_id} → {packet.get('target', 'broadcast')} "
            f"(type={packet['type']}, transport={transport})"
        )
        return route_gip_packet(packet, transport, options)
    except Exception as e:
        logger.error(f"[GlyphNetPacket] Failed to push packet via {transport}: {e}")
        return False