import os
import logging

logger = logging.getLogger(__name__)

class KeyManager:
    """
    Centralized encryption key manager.
    Loads key securely from environment or config.
    """

    # Default fallback key for testing only (32 bytes)
    DEFAULT_TEST_KEY = b"0123456789abcdef0123456789abcdef"

    def __init__(self):
        self._key = None
        self.load_key()

    def load_key(self):
        key_hex = os.getenv("GLYPHVAULT_ENCRYPTION_KEY_HEX")
        logger.info(f"Attempting to load GLYPHVAULT_ENCRYPTION_KEY_HEX: {key_hex}")
        if key_hex:
            try:
                key_bytes = bytes.fromhex(key_hex)
                if len(key_bytes) != 32:
                    raise ValueError("Encryption key must be 32 bytes (256 bits) long")
                self._key = key_bytes
                logger.info("GlyphVault encryption key loaded from environment")
            except Exception as e:
                logger.error(f"Failed to load GlyphVault encryption key from env: {e}")
                self._key = None
        else:
            logger.warning("No GlyphVault encryption key found in environment")
        
        if self._key is None:
            # Fallback to default test key with warning
            logger.warning("Using fallback default encryption key for testing purposes!")
            self._key = self.DEFAULT_TEST_KEY

    @property
    def key(self):
        if self._key is None:
            raise RuntimeError("Encryption key not loaded or invalid")
        return self._key


# Singleton instance
key_manager = KeyManager()