import json
import base64
import os
import logging
from typing import Optional, Dict, Any

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from backend.modules.exceptions.tampered_payload import TamperedPayloadError

logger = logging.getLogger(__name__)


class GWaveEncryptor:
    """
    Encrypts and decrypts GWave payloads using AES-GCM with a derived symmetric key.
    The key is derived from the GKey's `collapse_hash`, optionally using a per-packet salt.
    """

    def __init__(self, gkey_pair: dict, salt: Optional[bytes] = None, randomize_salt: bool = False):
        if "collapse_hash" not in gkey_pair:
            raise ValueError("GKey missing 'collapse_hash' for key derivation")

        self.gkey = gkey_pair
        self.salt = salt or (get_random_bytes(16) if randomize_salt else b'gwave-static-salt')
        self.key = self._derive_key(gkey_pair["collapse_hash"], self.salt)

    def _derive_key(self, collapse_hash: str, salt: bytes) -> bytes:
        return PBKDF2(collapse_hash, salt, dkLen=32, count=150000)

    def encrypt_payload(self, payload: Dict[str, Any], passthrough_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        try:
            plaintext = json.dumps(payload).encode("utf-8")
            nonce = get_random_bytes(12)
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
            ciphertext, tag = cipher.encrypt_and_digest(plaintext)

            result = {
                "qkd_encrypted": True,
                "payload": base64.b64encode(ciphertext).decode("utf-8"),
                "nonce": base64.b64encode(nonce).decode("utf-8"),
                "tag": base64.b64encode(tag).decode("utf-8"),
                "salt": base64.b64encode(self.salt).decode("utf-8"),
                "encryption_scheme": "AES-GCM",
            }

            if passthrough_metadata:
                for k, v in passthrough_metadata.items():
                    if k not in result:
                        result[k] = v

            return result

        except Exception as e:
            logger.error(f"[QKD Encrypt] Failed to encrypt GWave payload: {e}")
            raise

    def decrypt_payload(self, encrypted: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt a base64-encoded AES-GCM ciphertext back to a payload dictionary.
        """
        try:
            # Use flat dict structure - not nested in "encrypted"
            nonce = base64.b64decode(encrypted["nonce"])
            tag = base64.b64decode(encrypted["tag"])
            ciphertext = base64.b64decode(encrypted["payload"])
            salt = base64.b64decode(encrypted.get("salt", "Z3dhdmUtc3RhdGljLXNhbHQ="))  # fallback static salt

            key = self._derive_key(self.gkey["collapse_hash"], salt)
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)

            return json.loads(plaintext.decode("utf-8"))

        except (ValueError, KeyError, json.JSONDecodeError) as e:
            logger.error(f"[QKD Decrypt] Payload decryption failed: {e}")
            raise TamperedPayloadError() from e