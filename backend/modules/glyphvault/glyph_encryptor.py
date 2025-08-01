import logging
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator  # ✅ Safe accessor

logger = logging.getLogger(__name__)

class GlyphEncryptor:
    """
    GlyphEncryptor handles encryption and decryption of data blocks stored inside `.dc` containers,
    enforcing access control via avatar state and supporting recursive unlocking logic.
    """

    NONCE_SIZE = 12  # AES-GCM standard nonce size

    def __init__(self, key: bytes):
        """
        Initialize the GlyphEncryptor with a symmetric encryption key.
        
        Args:
            key (bytes): A 256-bit key used for AES-GCM encryption/decryption.
        """
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes (256 bits) long")
        self.key = key
        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """
        Encrypt plaintext data into an encrypted block with optional associated data for integrity.
        
        Args:
            plaintext (bytes): The data to encrypt.
            associated_data (Optional[bytes]): Additional data authenticated but not encrypted.
        
        Returns:
            bytes: The encrypted data with nonce prepended.
        """
        nonce = os.urandom(self.NONCE_SIZE)
        encrypted = self.aesgcm.encrypt(nonce, plaintext, associated_data)
        logger.debug(f"Encrypted data block of length {len(plaintext)} bytes with nonce {nonce.hex()}")
        return nonce + encrypted

    def decrypt(self, ciphertext: bytes, associated_data: Optional[bytes] = None,
                avatar_state: Optional[dict] = None) -> Optional[bytes]:
        """
        Decrypt ciphertext data if avatar state permits access.
        
        Args:
            ciphertext (bytes): The encrypted data with nonce prepended.
            associated_data (Optional[bytes]): Additional data authenticated but not encrypted.
            avatar_state (Optional[dict]): Avatar state dict used for access control checks.
        
        Returns:
            Optional[bytes]: The decrypted plaintext or None if access denied or decryption fails.
        """
        if not self._check_avatar_state(avatar_state):
            logger.warning("Decryption denied: invalid avatar state")
            return None

        try:
            nonce = ciphertext[:self.NONCE_SIZE]
            encrypted = ciphertext[self.NONCE_SIZE:]
            plaintext = self.aesgcm.decrypt(nonce, encrypted, associated_data)
            logger.debug(f"Decrypted data block of length {len(plaintext)} bytes with nonce {nonce.hex()}")
            return plaintext
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None

    def _check_avatar_state(self, avatar_state: Optional[dict]) -> bool:
        """
        Check if the current avatar state satisfies access control requirements to decrypt.
        
        Args:
            avatar_state (Optional[dict]): Avatar state to verify.
        
        Returns:
            bool: True if access allowed, False otherwise.
        """
        soul_law = get_soul_law_validator()  # ✅ Lazy load validator safely
        return soul_law.validate_avatar(avatar_state)

    def recursive_unlock(self, ciphertext: bytes, associated_data: Optional[bytes],
                         avatar_state: Optional[dict], max_depth: int = 5) -> Optional[bytes]:
        """
        Recursively decrypt nested encrypted blocks, unlocking successive layers as permitted.
        
        Args:
            ciphertext (bytes): Encrypted data block.
            associated_data (Optional[bytes]): Associated authenticated data.
            avatar_state (Optional[dict]): Avatar state for access control.
            max_depth (int): Maximum recursion depth to prevent infinite loops.
        
        Returns:
            Optional[bytes]: Fully decrypted data or None if any layer fails.
        """
        if max_depth <= 0:
            logger.error("Maximum recursive unlock depth reached; aborting")
            return None

        plaintext = self.decrypt(ciphertext, associated_data, avatar_state)
        if plaintext is None:
            return None

        # TODO: Detect if plaintext contains further encrypted layers and recursively decrypt.
        # This requires defining a format or marker for nested blocks.
        return plaintext


# ✅ Utility function (outside the class)
def is_encrypted_block(glyph: str) -> bool:
    """
    Detect if a glyph string is an encrypted block.
    Typically checks for a known prefix or structural marker (e.g., ENC: or 🔒).
    """
    if not isinstance(glyph, str):
        return False
    return glyph.startswith("ENC:") or glyph.startswith("🔒")

# End of glyph_encryptor.py