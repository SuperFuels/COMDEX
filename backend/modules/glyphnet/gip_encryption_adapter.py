# backend/modules/glyphnet/gip_encryption_adapter.py

import base64
import json
import logging
from typing import Dict, Any, Optional

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from backend.modules.codex.codex_crypto import qglyph_encrypt, qglyph_decrypt

logger = logging.getLogger(__name__)

DEFAULT_AES_KEY = get_random_bytes(32)  # AES-256

def encrypt_gip_packet(packet: Dict[str, Any], mode: str = "qglyph", key: Optional[bytes] = None) -> str:
    """
    Encrypts a symbolic GIP packet.
    Modes:
    - "qglyph": Symbolic QGlyph encryption
    - "aes": AES-256 encryption
    Returns base64-encoded string.
    """
    try:
        raw_json = json.dumps(packet)
        if mode == "qglyph":
            return qglyph_encrypt(raw_json)
        elif mode == "aes":
            key = key or DEFAULT_AES_KEY
            cipher = AES.new(key, AES.MODE_EAX)
            ciphertext, tag = cipher.encrypt_and_digest(raw_json.encode())
            return base64.b64encode(cipher.nonce + tag + ciphertext).decode()
        else:
            raise ValueError(f"Unknown encryption mode: {mode}")
    except Exception as e:
        logger.exception("[Encryptor] Failed to encrypt")
        return ""

def decrypt_gip_packet(encoded: str, mode: str = "qglyph", key: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
    """
    Decrypts a symbolic GIP packet.
    Returns dict or None.
    """
    try:
        if mode == "qglyph":
            decrypted = qglyph_decrypt(encoded)
            return json.loads(decrypted)
        elif mode == "aes":
            raw = base64.b64decode(encoded)
            nonce, tag, ciphertext = raw[:16], raw[16:32], raw[32:]
            key = key or DEFAULT_AES_KEY
            cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
            plain = cipher.decrypt_and_verify(ciphertext, tag)
            return json.loads(plain.decode())
        else:
            raise ValueError(f"Unknown decryption mode: {mode}")
    except Exception as e:
        logger.exception("[Decryptor] Failed to decrypt")
        return None