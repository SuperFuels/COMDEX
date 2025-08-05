import json
import time
import base64
import logging
from typing import Dict, Any, Optional

# ✅ Use AES-based encryption as the primary encrypt function (backward-compatible alias)
from ..glyphnet.glyphnet_crypto import aes_encrypt_packet as encrypt_packet, aes_decrypt_packet as decrypt_packet

# ✅ Ephemeral key manager for temporary session keys
from ..glyphnet.ephemeral_key_manager import get_ephemeral_key_manager

# ✅ Symbolic key derivation for advanced entropy-driven keys
from ..glyphnet.symbolic_key_derivation import symbolic_key_deriver

logger = logging.getLogger(__name__)

def create_gip_packet(payload: Dict[str, Any], sender: str, target: Optional[str] = None, packet_type: str = "glyph_push", 
                      encrypt: bool = False, public_key_pem: Optional[bytes] = None, ephemeral_session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a standardized GlyphNet .gip packet with metadata.
    Optionally encrypts the payload if encrypt=True and keys are provided.

    Args:
        payload: The symbolic payload dictionary to send.
        sender: The sender's identity string.
        target: Optional target identity string for directed packets.
        packet_type: Type of packet; defaults to "glyph_push".
        encrypt: Whether to encrypt the payload.
        public_key_pem: The recipient's public key PEM bytes for encryption.
        ephemeral_session_id: Session ID to get ephemeral AES key fallback.

    Returns:
        A dict representing the .gip packet ready for transmission.
    """
    packet = {
        "type": packet_type,
        "sender": sender,
        "payload": None,
        "timestamp": time.time(),
    }
    if target:
        packet["target"] = target

    try:
        if encrypt:
            if public_key_pem:
                # RSA encrypt
                encrypted_payload = encrypt_packet(payload, public_key_pem)
                packet["payload"] = encrypted_payload
                packet["type"] = f"{packet_type}_encrypted"
            elif ephemeral_session_id:
                # AES fallback encrypt with ephemeral key, with symbolic semantic parameters
                ephemeral_manager = get_ephemeral_key_manager()

                # Define symbolic semantic parameters for key derivation
                symbolic_trust = 0.7
                symbolic_emotion = 0.5
                seed_phrase = f"GIP:{sender}->{ephemeral_session_id}"

                aes_key = ephemeral_manager.get_key(ephemeral_session_id)
                if aes_key is None:
                    # Generate ephemeral key with symbolic context
                    aes_key = ephemeral_manager.generate_key(
                        ephemeral_session_id,
                        trust_level=symbolic_trust,
                        emotion_level=symbolic_emotion,
                        seed_phrase=seed_phrase
                    )
                if aes_key:
                    encrypted_payload = aes_encrypt_packet(payload, aes_key)
                    packet["payload"] = encrypted_payload
                    packet["type"] = f"{packet_type}_encrypted_aes_ephemeral"
                else:
                    logger.warning(f"[GlyphNetPacket] No ephemeral AES key found for session {ephemeral_session_id}. Sending unencrypted.")
                    packet["payload"] = payload
            else:
                logger.warning(f"[GlyphNetPacket] Encryption requested but no key provided. Sending unencrypted.")
                packet["payload"] = payload
        else:
            packet["payload"] = payload
    except Exception as e:
        logger.error(f"[GlyphNetPacket] Payload encryption failed: {e}")
        raise

    return packet

def encode_gip_packet(packet: Dict[str, Any]) -> str:
    """
    Serialize and base64-encode a GlyphNet packet for transmission.

    Args:
        packet: The GlyphNet packet dict.

    Returns:
        Base64-encoded JSON string of the packet.
    """
    try:
        json_str = json.dumps(packet)
        encoded = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
        return encoded
    except Exception as e:
        logger.error(f"[GlyphNetPacket] Encoding failed: {e}")
        raise

def decode_gip_packet(encoded_packet: str) -> Dict[str, Any]:
    """
    Decode a base64 GlyphNet packet and deserialize JSON.

    Args:
        encoded_packet: Base64-encoded JSON string.

    Returns:
        The decoded GlyphNet packet dict.
    """
    try:
        json_str = base64.b64decode(encoded_packet).decode("utf-8")
        packet = json.loads(json_str)
        return packet
    except Exception as e:
        logger.error(f"[GlyphNetPacket] Decoding failed: {e}")
        raise

def decrypt_gip_packet(encrypted_payload: str, private_key_pem: bytes) -> Dict[str, Any]:
    """
    Decrypts an encrypted payload string to the original dict using RSA.

    Args:
        encrypted_payload: Base64 string of encrypted payload.
        private_key_pem: PEM bytes of the private key.

    Returns:
        Decrypted payload dict.
    """
    try:
        decrypted = decrypt_packet(encrypted_payload, private_key_pem)
        return decrypted
    except Exception as e:
        logger.error(f"[GlyphNetPacket] Decryption failed: {e}")
        raise

def push_symbolic_packet(packet: Dict[str, Any]) -> bool:
    """
    Send the packet into the GlyphNet backend or transport layer.
    This is a stub function: replace with your actual transport logic.

    Args:
        packet: GlyphNet packet dict.

    Returns:
        True if push succeeded, False otherwise.
    """
    try:
        logger.info(f"[GlyphNetPacket] Pushing packet from {packet.get('sender')} to {packet.get('target', 'broadcast')}")
        # TODO: Implement real transmission here, e.g. WebSocket, radio, beacon, etc.
        return True
    except Exception as e:
        logger.error(f"[GlyphNetPacket] Failed to push packet: {e}")
        return False

### Notes & Future Enhancements
# - Timestamp uses epoch seconds; consider ISO 8601 for clarity.
# - Add support for chunked large packet transmission.
# - Integrate with GlyphNet transport modules: websocket, radio, beacon.
# - Add message signing and signature verification for authenticity.
# - Implement retry and acknowledgement for reliable delivery.
# - Add metadata flags: encrypted, compressed, signed.
# - Support group encryption and multi-recipient packets.
# - Add compression before encryption for bandwidth savings.
# - Add cryptographic nonce or IV for AES fallback encryption.
# - Future support for quantum-resistant encryption schemes.